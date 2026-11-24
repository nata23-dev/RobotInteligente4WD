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

log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, bridge, stop_bridge, config):
        self.bridge, self.stop_bridge, self.config = bridge, stop_bridge, config
        self.safety = Safety()
        self.queue = queue.Queue(maxsize=8)
        self.closed = threading.Event()
        self.worker = threading.Thread(target=self._run, name='despacho', daemon=True)
        self.supervisor = threading.Thread(target=self._supervise, name='seguridad', daemon=True)
        self.stop_lock = threading.Lock()
        self.stop_thread = None
        self.state = {}
        self.health = {}
        self.seq = 0
        self.last_heartbeat = 0.
        self.last_poll = 0.
        self.response_ms = None
        self.active = False

    def start(self):
        self.worker.start()
        self.supervisor.start()

    def submit(self, command):
        future = Future()
        with self.safety.lock:
            if self.closed.is_set():
                future.set_exception(RuntimeError('Despachador cerrado'))
                return future
            generation = self.safety.generation
            if command.action in ('drive', 'servo', 'enable'):
                try:
                    self.safety.require(command.owner, generation)
                except PermissionError as exc:
                    future.set_exception(exc)
                    return future
            try:
                self.queue.put_nowait((generation, time.monotonic(), command, future))
            except queue.Full:
                future.set_exception(RuntimeError('Cola llena: orden descartada'))
        return future

    def _cancel(self):
        while True:
            try:
                _, _, _, future = self.queue.get_nowait()
                future.cancel()
            except queue.Empty:
                return

    def stop(self, reason='Parada solicitada'):
        with self.safety.lock:
            self.safety.invalidate(reason + ' / no confirmada')
            self._cancel()
        # Solo un trabajador STOP; invalida de nuevo aunque ya exista una petición.
        with self.stop_lock:
            if self.stop_thread and self.stop_thread.is_alive():
                return
            self.stop_thread = threading.Thread(target=self._stop_remote, name='stop-prioritario', daemon=True)
            self.stop_thread.start()

    def _stop_remote(self):
        try:
            while True:
                with self.safety.lock:
                    generation = self.safety.generation
                self.stop_bridge.request('stop')
                state = validate_state(self.stop_bridge.request('state'))
                confirmed = (not state['armed'] and not state['motor_activo'] and
                             state['garra'] == state['garra_objetivo'] and state['base'] == state['base_objetivo'])
                with self.safety.lock:
                    if generation != self.safety.generation:
                        continue
                    self.state = state
                    self.safety.status = 'Parada confirmada (estado lógico)' if confirmed else 'Parada no confirmada'
                    break
        except (APIError, ValueError):
            with self.safety.lock:
                self.safety.connected = False
                self.safety.status = 'Parada no confirmada / pérdida de comunicación'
            log.warning('STOP no confirmado')

    def _poll(self):
        state = validate_state(self.bridge.request('state'))
        with self.safety.lock:
            self.state = state
            if self.safety.session and not state['armed']:
                self.safety.invalidate('Sesión perdida / requiere rearme explícito')
                self._cancel()
        self.last_poll = time.monotonic()
        return state

    def _execute(self, gen, command):
        a, p = command.action, command.params.copy()
        if a == 'verify':
            health = self.bridge.request('health')
            validate_health(health)
            self._poll()
            with self.safety.lock:
                if gen != self.safety.generation:
                    raise PermissionError('Verificación cancelada')
                self.health = health
                self.safety.connected = True
                self.safety.status = 'Verificado / armado explícito requerido'
            return health
        if a == 'arm':
            with self.safety.lock:
                if (not self.safety.connected or self.safety.session or self.safety.mode != 'manual'
                    or time.monotonic() - self.safety.controller_at > self.config['controller_lease_s']
                    or (self.stop_thread and self.stop_thread.is_alive())):
                    raise PermissionError('No se permite armar en este estado')
            state = self._poll()
            if state['armed'] or state['maintenance']:
                raise PermissionError('El firmware ya está armado o en mantenimiento; detener primero')
            with self.safety.lock:
                if gen != self.safety.generation:
                    raise PermissionError('Armado cancelado')
            result = self.bridge.request('arm', {'challenge': state['challenge']})
            integer(result.get('session'), 1, 0xffffffff, 'session')
            with self.safety.lock:
                if gen != self.safety.generation:
                    # Una respuesta de arm puede llegar después de STOP: invalidar también remotamente.
                    self.stop('Armado cancelado durante solicitud')
                    raise PermissionError('Armado cancelado')
                self.safety.session = result['session']
                self.safety.status = 'Armado manual explícitamente'
                self.seq = 0
                self.last_heartbeat = time.monotonic()
            return result
        if a == 'release':
            if p.get('confirm') != 1:
                raise PermissionError('Sujete el brazo y confirme liberación')
            with self.safety.lock:
                if not self.safety.connected or self.safety.session:
                    raise PermissionError('Detener y verificar antes de liberar')
            state = self._poll()
            if state['armed']:
                raise PermissionError('Firmware armado; detener antes de liberar')
            return self.bridge.request(a, p)
        if a not in SEQUENCED:
            raise ValueError('Acción no autorizada')
        if a == 'drive':
            pattern([p[k] for k in ('fl', 'fr', 'rl', 'rr')])
            integer(p['ms'], self.config['pulse_min_ms'], self.config['pulse_max_ms'], 'ms')
        if a == 'servo':
            limits = self.config['servos'][p['nombre']]
            integer(p['grado'], limits['min'], limits['max'], 'grado')
        with self.safety.lock:
            self.safety.require(command.owner, gen)
            if time.monotonic() - self.safety.controller_at > self.config['controller_lease_s']:
                raise PermissionError('Controlador sin señal de salud')
            self.seq += 1
            p.update(session=self.safety.session, seq=self.seq)
        return self.bridge.request(a, p)

    def _failure(self, exc):
        # Un rechazo físico de interlock no invalida la sesión ni se reintenta.
        if isinstance(exc, APIError) and exc.error in ('actuators_busy', 'servo_not_enabled'):
            return
        if isinstance(exc, (APIError, ValueError)):
            with self.safety.lock:
                self.safety.connected = False
            self.stop('Error de comunicación o protocolo')

    def _run(self):
        while not self.closed.is_set():
            try:
                now = time.monotonic()
                with self.safety.lock:
                    session = self.safety.session
                    gen = self.safety.generation
                    healthy = now - self.safety.controller_at <= self.config['controller_lease_s']
                if session and healthy and now - self.last_heartbeat >= self.config['heartbeat_s']:
                    self._execute(gen, Command('heartbeat'))
                    self.last_heartbeat = time.monotonic()
                if self.safety.connected and now - self.last_poll >= .35:
                    self._poll()
                try:
                    gen, created, command, future = self.queue.get(timeout=.025)
                except queue.Empty:
                    continue
                if not future.set_running_or_notify_cancel():
                    continue
                self.active = True
                try:
                    if gen != self.safety.generation:
                        raise PermissionError('Orden cancelada por parada o cambio de modo')
                    if command.action in SEQUENCED and time.monotonic() - created > .3:
                        raise PermissionError('Orden atrasada descartada')
                    start = time.monotonic()
                    result = self._execute(gen, command)
                    self.response_ms = (time.monotonic() - start) * 1000
                    future.set_result(result)
                    log.info('Orden %s completada', command.action)
                except Exception as exc:
                    self._failure(exc)
                    future.set_exception(exc)
                finally:
                    self.active = False
            except (APIError, ValueError) as exc:
                self._failure(exc)
            except Exception:
                log.exception('Fallo interno del despachador')
                self.stop('Fallo del despachador')
                self.closed.set()
        self._cancel()

    def _supervise(self):
        while not self.closed.wait(.05):
            with self.safety.lock:
                unhealthy = bool(self.safety.session) and (not self.worker.is_alive() or
                    time.monotonic() - self.safety.controller_at > self.config['controller_lease_s'])
            if unhealthy:
                self.stop('Controlador sin señal de salud')

    def close(self):
        with self.safety.lock:
            should_stop = self.safety.connected or bool(self.safety.session)
        if should_stop:
            self.stop('Cierre de aplicación')
        self.closed.set()
        for thread in (self.worker, self.supervisor):
            if thread.ident:
                thread.join(2)
        if self.stop_thread:
            self.stop_thread.join(2)
        if self.worker.is_alive() or (self.stop_thread and self.stop_thread.is_alive()):
            raise RuntimeError('Comunicación aún terminando; no iniciar nuevo despachador')
        self.bridge.close()
        if self.stop_bridge is not self.bridge:
            self.stop_bridge.close()
