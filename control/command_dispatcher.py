"""Único emisor secuenciado; STOP fuera de la cola y con transporte propio."""

from concurrent.futures import Future
import logging
import queue
import threading
import time
from app.config import integer, pattern
from app.models import Command
from hardware.protocol import APIError, SEQUENCED, validate_health, validate_state
from control.safety import Safety
from control.communication import (
    Communication,
    RETRY_DELAYS,
    STATE_MAX_AGE_S,
    HEARTBEAT_CONFIRMATION_LIMIT_S,
)
from hardware.telemetry import error_kind

log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(
        self, bridge, stop_bridge, config, recovery_bridge=None, heartbeat_bridge=None
    ):
        self.bridge, self.stop_bridge, self.config = bridge, stop_bridge, config
        self.recovery_bridge = recovery_bridge or bridge
        self.heartbeat_bridge = heartbeat_bridge or bridge
        self.communication = Communication()
        self.recovery_enabled = False
        self.recovery_suspended = threading.Event()
        self.retry_delays = RETRY_DELAYS
        self.next_retry = 0.0
        self.safety = Safety()
        self.queue = queue.Queue(maxsize=8)
        self.closed = threading.Event()
        self.worker = threading.Thread(target=self._run, name="despacho", daemon=True)
        self.supervisor = threading.Thread(
            target=self._supervise, name="seguridad", daemon=True
        )
        self.stop_lock = threading.Lock()
        self.stop_thread = None
        self.state = {}
        self.health = {}
        self.seq = 0
        self.last_heartbeat = 0.0
        self.last_poll = 0.0
        self.response_ms = None
        self.active = False
        # Exclusión de admisión de órdenes y almacenamiento; STOP nunca la usa.
        self.capture_gate = threading.Lock()
        self.state_confirmed_at = 0.0

    def start(self):
        self.worker.start()
        self.supervisor.start()

    def submit(self, command):
        future = Future()
        if not self.capture_gate.acquire(blocking=False):
            future.set_exception(PermissionError("Orden descartada durante captura"))
            return future
        try:
            return self._submit(command, future)
        finally:
            self.capture_gate.release()

    def _submit(self, command, future):
        with self.safety.lock:
            if self.closed.is_set():
                future.set_exception(RuntimeError("Despachador cerrado"))
                return future
            generation = self.safety.generation
            if command.action in ("drive", "servo", "enable"):
                try:
                    self.safety.require(command.owner, generation)
                except PermissionError as exc:
                    future.set_exception(exc)
                    return future
            try:
                self.queue.put_nowait((generation, time.monotonic(), command, future))
            except queue.Full:
                future.set_exception(RuntimeError("Cola llena: orden descartada"))
        return future

    def _cancel(self):
        while True:
            try:
                _, _, _, future = self.queue.get_nowait()
                future.cancel()
            except queue.Empty:
                return

    def stop(self, reason="Parada solicitada"):
        with self.safety.lock:
            self.safety.invalidate(reason + " / no confirmada")
            self.state_confirmed_at = 0.0
            self.communication.stop_state = "Pendiente de confirmación"
            self._cancel()
        # Solo un trabajador STOP; invalida de nuevo aunque ya exista una petición.
        with self.stop_lock:
            if self.stop_thread and self.stop_thread.is_alive():
                return
            self.stop_thread = threading.Thread(
                target=self._stop_remote, name="stop-prioritario", daemon=True
            )
            self.stop_thread.start()

    def _stop_remote(self):
        try:
            while True:
                with self.safety.lock:
                    generation = self.safety.generation
                self._request(self.stop_bridge, "stop")
                started = time.monotonic()
                state = self._request(
                    self.stop_bridge, "state", validator=validate_state
                )
                confirmed = (
                    self._idle(state) and time.monotonic() - started <= STATE_MAX_AGE_S
                )
                with self.safety.lock:
                    if generation != self.safety.generation:
                        continue
                    self.state = state
                    self.state_confirmed_at = started if confirmed else 0.0
                    self.communication.stop_state = (
                        "Confirmado (estado lógico)" if confirmed else "No confirmado"
                    )
                    if not confirmed:
                        self.safety.connected = False
                    self.safety.status = (
                        "Parada confirmada (estado lógico)"
                        if confirmed
                        else "Parada no confirmada"
                    )
                    break
        except (APIError, ValueError) as exc:
            with self.safety.lock:
                self.safety.connected = False
                self.safety.status = "Parada no confirmada / pérdida de comunicación"
                self.state_confirmed_at = 0.0
                self.communication.stop_state = "No confirmado"
            if self.communication.outage_started is None:
                self.communication.failed(error_kind(exc))
            self.next_retry = max(
                self.next_retry, time.monotonic() + self.retry_delays[0]
            )
            # Una única transición visible; los intentos permanecen en métricas.
            self.communication.set_state("Estado remoto desconocido")

    @staticmethod
    def _idle(state):
        if not isinstance(state, dict) or any(
            k not in state
            for k in (
                "armed",
                "motor_activo",
                "brazo_ocupado",
                "maintenance",
                "directions",
                "garra",
                "garra_objetivo",
                "base",
                "base_objetivo",
            )
        ):
            return False
        return (
            not state["armed"]
            and not state["motor_activo"]
            and not state["brazo_ocupado"]
            and not state["maintenance"]
            and not any(state["directions"])
            and state["garra"] == state["garra_objetivo"]
            and state["base"] == state["base_objetivo"]
        )

    def _request(self, bridge, action, params=None, validator=None):
        started = time.monotonic()
        try:
            result = bridge.request(action, params)
            if validator:
                validator(result)
        except Exception as exc:
            self.communication.requests.record(started, False, error_kind(exc))
            raise
        self.communication.requests.record(started, True)
        return result

    def _poll(self, gen=None, bridge=None):
        gen = self.safety.generation if gen is None else gen
        started = time.monotonic()
        state = self._request(bridge or self.bridge, "state", validator=validate_state)
        with self.safety.lock:
            if self.closed.is_set() or gen != self.safety.generation:
                raise PermissionError("Estado descartado por cambio de generación")
            if time.monotonic() - started > STATE_MAX_AGE_S:
                raise APIError("stale_state", category="stale_response")
            self.state = state
            self.state_confirmed_at = started
            if self.safety.session and not state["armed"]:
                self.safety.invalidate("Sesión perdida / requiere rearme explícito")
                self._cancel()
        self.last_poll = time.monotonic()
        return state

    def _verify(self, gen, recovering=False):
        with self.safety.lock:
            if (
                self.closed.is_set()
                or self.recovery_suspended.is_set()
                or gen != self.safety.generation
            ):
                raise PermissionError("Verificación suspendida o cancelada")
            self.recovery_enabled = True
        self.communication.set_state("Reconectando" if recovering else "Conectando")
        transport = self.recovery_bridge if recovering else self.bridge
        health = self._request(transport, "health", validator=validate_health)
        if self.closed.is_set() or gen != self.safety.generation:
            raise PermissionError("Verificación cancelada")
        state = self._poll(gen, transport)
        with self.safety.lock:
            if self.closed.is_set() or gen != self.safety.generation:
                raise PermissionError("Verificación cancelada")
            if not self._idle(state):
                self.safety.connected = False
                self.communication.set_state("Estado remoto desconocido")
                self.stop("Estado remoto no está en reposo; verificar STOP")
                self.next_retry = time.monotonic() + self.retry_delays[-1]
                raise PermissionError(
                    "Recuperación bloqueada hasta confirmar reposo lógico"
                )
            self.health = health
            self.safety.connected = True
            self.safety.status = "Verificado / armado explícito requerido"
            self.communication.recovered()
            if self.communication.stop_state == "No confirmado":
                self.communication.stop_state = (
                    "Reposo confirmado por lectura; STOP previo sin confirmar"
                )
        return health

    def _recover(self):
        if (
            not self.recovery_enabled
            or self.safety.connected
            or self.safety.session
            or self.closed.is_set()
            or self.recovery_suspended.is_set()
            or time.monotonic() < self.next_retry
        ):
            return
        if self.stop_thread and self.stop_thread.is_alive():
            return
        gen = self.safety.generation
        try:
            self._verify(gen, recovering=True)
        except PermissionError:
            self.next_retry = max(
                self.next_retry, time.monotonic() + self.retry_delays[0]
            )
        except (APIError, ValueError) as exc:
            self._failure(exc, recovering=True)

    def suspend_recovery(self):
        self.recovery_suspended.set()
        with self.safety.lock:
            self.safety.invalidate("Supervisión suspendida por cierre o configuración")
            self.state_confirmed_at = 0.0
            self._cancel()

    def resume_recovery(self):
        if not self.closed.is_set():
            self.recovery_suspended.clear()

    def communication_snapshot(self):
        result = self.communication.snapshot()
        age = (
            time.monotonic() - self.state_confirmed_at
            if self.state_confirmed_at
            else None
        )
        result["state_age_s"] = age
        result["remote_state"] = (
            "Desconocido"
            if self.closed.is_set()
            or not self.safety.connected
            or age is None
            or age > STATE_MAX_AGE_S
            else (
                "Armado"
                if self.state.get("armed")
                else (
                    "Desarmado / reposo lógico"
                    if self._idle(self.state)
                    else "Actuadores ocupados"
                )
            )
        )
        if self.safety.session:
            result["remote_state"] = "Armado aceptado (ACK); sin telemetría reciente"
        result["local_authorized"] = bool(self.safety.session)
        return result

    def _execute(self, gen, command):
        a, p = command.action, command.params.copy()
        if a == "verify":
            if self.safety.session:
                raise PermissionError("Detenga antes de verificar de nuevo")
            return self._verify(gen)
        if a == "arm":
            with self.safety.lock:
                if (
                    not self.safety.connected
                    or self.safety.session
                    or self.safety.mode != "manual"
                    or time.monotonic() - self.safety.controller_at
                    > self.config["controller_lease_s"]
                    or (self.stop_thread and self.stop_thread.is_alive())
                ):
                    raise PermissionError("No se permite armar en este estado")
            state = self._poll(gen)
            if not self._idle(state):
                raise PermissionError(
                    "El firmware ya está armado o en mantenimiento; detener primero"
                )
            with self.safety.lock:
                if gen != self.safety.generation:
                    raise PermissionError("Armado cancelado")
            result = self._request(
                self.bridge, "arm", {"challenge": state["challenge"]}
            )
            integer(result.get("session"), 1, 0xFFFFFFFF, "session")
            with self.safety.lock:
                if gen != self.safety.generation:
                    # Una respuesta de arm puede llegar después de STOP: invalidar también remotamente.
                    self.stop("Armado cancelado durante solicitud")
                    raise PermissionError("Armado cancelado")
                self.safety.session = result["session"]
                self.safety.status = "Armado manual explícitamente"
                self.seq = 0
                self.last_heartbeat = time.monotonic()
                self.state_confirmed_at = 0.0
            return result
        if a == "release":
            if p.get("confirm") != 1:
                raise PermissionError("Sujete el brazo y confirme liberación")
            with self.safety.lock:
                if not self.safety.connected or self.safety.session:
                    raise PermissionError("Detener y verificar antes de liberar")
            state = self._poll(gen)
            if state["armed"]:
                raise PermissionError("Firmware armado; detener antes de liberar")
            return self._request(self.bridge, a, p)
        if a not in SEQUENCED:
            raise ValueError("Acción no autorizada")
        if a == "drive":
            pattern([p[k] for k in ("fl", "fr", "rl", "rr")])
            integer(
                p["ms"], self.config["pulse_min_ms"], self.config["pulse_max_ms"], "ms"
            )
        if a == "servo":
            limits = self.config["servos"][p["nombre"]]
            integer(p["grado"], limits["min"], limits["max"], "grado")
        with self.safety.lock:
            self.safety.require(command.owner, gen)
            if (
                time.monotonic() - self.safety.controller_at
                > self.config["controller_lease_s"]
            ):
                raise PermissionError("Controlador sin señal de salud")
            self.seq += 1
            p.update(session=self.safety.session, seq=self.seq)
        return self._request(
            self.heartbeat_bridge if a == "heartbeat" else self.bridge, a, p
        )

    def _failure(self, exc, recovering=False):
        # Un rechazo físico de interlock no invalida la sesión ni se reintenta.
        if isinstance(exc, APIError) and exc.error in (
            "actuators_busy",
            "servo_not_enabled",
        ):
            return
        if isinstance(exc, (APIError, ValueError)):
            with self.safety.lock:
                self.safety.connected = False
                self.state_confirmed_at = 0.0
            self.communication.failed(error_kind(exc))
            self.next_retry = (
                time.monotonic()
                + self.retry_delays[
                    min(self.communication.consecutive - 1, len(self.retry_delays) - 1)
                ]
            )
            if recovering:
                with self.safety.lock:
                    self.safety.invalidate(
                        "Reconexión sin estado válido / movimiento bloqueado"
                    )
                    self._cancel()
            else:
                self.stop("Error de comunicación o protocolo")

    def _run(self):
        while not self.closed.is_set():
            try:
                now = time.monotonic()
                with self.safety.lock:
                    session = self.safety.session
                    gen = self.safety.generation
                    healthy = (
                        now - self.safety.controller_at
                        <= self.config["controller_lease_s"]
                    )
                if (
                    session
                    and healthy
                    and now - self.last_heartbeat >= self.config["heartbeat_s"]
                ):
                    self._execute(gen, Command("heartbeat"))
                    self.last_heartbeat = time.monotonic()
                # Telemetría no compite con heartbeat durante autorización armada.
                if (
                    self.safety.connected
                    and not self.safety.session
                    and not self.recovery_suspended.is_set()
                    and now - self.last_poll >= 0.35
                ):
                    state = self._poll()
                    if not self._idle(state):
                        self.safety.connected = False
                        self.communication.set_state("Estado remoto desconocido")
                        self.stop("Actuadores o armado inesperados durante supervisión")
                        self.next_retry = time.monotonic() + self.retry_delays[0]
                    else:
                        self.communication.recovered()
                self._recover()
                try:
                    gen, created, command, future = self.queue.get(timeout=0.025)
                except queue.Empty:
                    continue
                if not future.set_running_or_notify_cancel():
                    continue
                if not self.capture_gate.acquire(blocking=False):
                    future.set_exception(
                        PermissionError("Orden descartada durante captura")
                    )
                    continue
                self.active = True
                try:
                    if gen != self.safety.generation:
                        raise PermissionError(
                            "Orden cancelada por parada o cambio de modo"
                        )
                    if command.action in SEQUENCED and time.monotonic() - created > 0.3:
                        raise PermissionError("Orden atrasada descartada")
                    start = time.monotonic()
                    result = self._execute(gen, command)
                    self.response_ms = (time.monotonic() - start) * 1000
                    future.set_result(result)
                    log.info("Orden %s completada", command.action)
                except Exception as exc:
                    self._failure(exc)
                    future.set_exception(exc)
                finally:
                    self.active = False
                    self.capture_gate.release()
            except PermissionError:
                # Lectura cancelada por STOP/cambio de modo/configuración.
                continue
            except (APIError, ValueError) as exc:
                self._failure(exc)
            except Exception as exc:
                log.error("Fallo interno del despachador (%s)", type(exc).__name__)
                with self.safety.lock:
                    self.safety.connected = False
                    self.state_confirmed_at = 0.0
                self.communication.failed("internal")
                self.communication.set_state("Comunicación perdida")
                self.stop("Fallo del despachador")
                self.closed.set()
        self._cancel()

    def _supervise(self):
        while not self.closed.wait(0.05):
            with self.safety.lock:
                unhealthy = bool(self.safety.session) and (
                    not self.worker.is_alive()
                    or time.monotonic() - self.safety.controller_at
                    > self.config["controller_lease_s"]
                    or time.monotonic() - self.last_heartbeat
                    > HEARTBEAT_CONFIRMATION_LIMIT_S
                )
            if unhealthy:
                self.stop("Controlador sin señal de salud")

    def close(self):
        self.recovery_enabled = False
        self.recovery_suspended.set()
        with self.safety.lock:
            should_stop = self.safety.connected or bool(self.safety.session)
        if should_stop:
            self.stop("Cierre de aplicación")
        self.closed.set()
        for thread in (self.worker, self.supervisor):
            if thread.ident:
                thread.join(2)
        if self.stop_thread:
            self.stop_thread.join(2)
        if self.worker.is_alive() or (self.stop_thread and self.stop_thread.is_alive()):
            raise RuntimeError(
                "Comunicación aún terminando; no iniciar nuevo despachador"
            )
        seen = set()
        for transport in (
            self.bridge,
            self.stop_bridge,
            self.recovery_bridge,
            self.heartbeat_bridge,
        ):
            if id(transport) not in seen:
                transport.close()
                seen.add(id(transport))
