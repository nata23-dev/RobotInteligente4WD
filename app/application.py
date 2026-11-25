"""Composición y tareas de disco/ciclo de vida fuera del hilo de Tkinter."""

import copy
import csv
from datetime import datetime
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
import queue
import threading
import time
from app.config import ROOT, LOCAL, load, save, validate, integer
from app.models import Command
from control.command_dispatcher import Dispatcher
from control.controller import Controller
from hardware.bridge import HTTPBridge
from hardware.camera import Camera
from hardware.simulator import Simulator
from dataset.capture import DatasetCapture
from ai.vision import VisionWorker
from dataset.burst import Burst


def setup_logging():
    (ROOT / "logs").mkdir(exist_ok=True)
    records = queue.Queue(maxsize=2000)
    handler = RotatingFileHandler(
        ROOT / "logs" / "robot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(QueueHandler(records))
    listener = QueueListener(records, handler, respect_handler_level=True)
    listener.start()
    return listener


class Application:
    def __init__(self, simulation=None):
        self.config = load()
        if simulation is not None:
            self.config["simulation"] = simulation
        self.events = queue.Queue(maxsize=100)
        self.jobs = queue.Queue(maxsize=8)
        self.closing = threading.Event()
        self.operation_lock = threading.Lock()
        self.capture_lock = threading.Lock()
        self.reconfiguring = False
        self.closed = False
        self.close_error = None
        self.lifecycle_failed = False
        self._compose()
        self.worker = threading.Thread(
            target=self._jobs, name="archivos-y-ciclo", daemon=True
        )
        self.worker.start()

    def _compose(self):
        c = copy.deepcopy(self.config)
        if c["simulation"]:
            bridge = stop_bridge = Simulator()
        else:
            bridge, stop_bridge = HTTPBridge(c), HTTPBridge(c)
        self.dispatcher = Dispatcher(bridge, stop_bridge, c)
        self.dispatcher.capture_gate = self.capture_lock
        self.controller = Controller(self.dispatcher)
        self.camera = Camera(c)
        self.vision = VisionWorker(self.camera, c)
        self.vision.start()
        destination = Path(c["dataset_dir"])
        self.dataset = DatasetCapture(
            destination if destination.is_absolute() else ROOT / destination
        )
        self.burst = Burst(
            self.camera.snapshot, self._capture_now, self.capture_guard, self.event
        )
        self.dispatcher.start()

    def event(self, kind, payload):
        try:
            self.events.put_nowait((kind, payload))
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            self.events.put_nowait((kind, payload))

    def job(self, fn, internal=False):
        if self.closing.is_set() or (self.reconfiguring and not internal):
            self.event("info", "Tarea descartada durante cierre o configuración")
            return False
        try:
            self.jobs.put_nowait(fn)
            return True
        except queue.Full:
            self.event("error", "Hay demasiadas tareas pendientes")
            return False

    def _jobs(self):
        while not self.closing.is_set():
            try:
                fn = self.jobs.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                with self.operation_lock:
                    if not self.closing.is_set():
                        fn()
            except Exception as exc:
                self.event("error", str(exc))

    def command(self, action, params=None):
        if self.reconfiguring or self.closing.is_set() or self.lifecycle_failed:
            self.event("error", "Aplicación cambiando configuración o cerrando")
            return
        if action == "arm" and self.burst.running:
            self.burst.cancel.set()
        if self.capture_lock.locked():
            self.event(
                "error", "Espere a que termine la captura antes de enviar órdenes"
            )
            return
        future = self.dispatcher.submit(Command(action, params or {}))

        def done(f):
            if f.cancelled():
                self.event("info", "Orden cancelada por seguridad")
                return
            try:
                f.result()
                self.event("info", action + ": completado (respuesta lógica)")
            except Exception as exc:
                self.event("error", str(exc))

        future.add_done_callback(done)

    def update_config(self, config):
        if self.lifecycle_failed:
            raise PermissionError(
                "Ciclo de vida incompleto; reinicie antes de reconfigurar"
            )
        new = validate(config)
        with self.dispatcher.safety.lock:
            if self.dispatcher.safety.session or self.dispatcher.state.get("armed"):
                raise PermissionError(
                    "Detenga el robot y confirme estado desarmado antes de configurar"
                )
            if (
                self.dispatcher.active
                or not self.dispatcher.queue.empty()
                or self.reconfiguring
            ):
                raise PermissionError("Espere a que terminen las tareas pendientes")
            self.reconfiguring = True
            self.dispatcher.safety.invalidate("Cambio de configuración")

        def apply():
            previous = self.config
            try:
                self.burst.stop()
                self.vision.stop()
                self.camera.stop()
                self.dispatcher.close()
                if self.dispatcher.safety.status.startswith("Parada no confirmada"):
                    raise PermissionError(
                        "Confirme la parada con el equipo anterior antes de cambiar configuración"
                    )
                save(new)
                self.config = new
                self._compose()
                self.event(
                    "configured",
                    "Configuración guardada. Conexión y armado explícitos requeridos.",
                )
            except Exception:
                threads = (
                    self.burst.thread,
                    self.vision.thread,
                    self.camera.thread,
                    self.dispatcher.worker,
                    self.dispatcher.supervisor,
                    self.dispatcher.stop_thread,
                )
                stopped = all(t is None or not t.is_alive() for t in threads)
                if stopped:
                    self.config = previous
                    self._compose()
                else:
                    self.lifecycle_failed = True
                    self.dispatcher.safety.invalidate(
                        "Ciclo de vida incompleto; reinicie la aplicación"
                    )
                raise
            finally:
                self.reconfiguring = False

        if not self.job(apply, internal=True):
            self.reconfiguring = False
            raise RuntimeError(
                "No se pudo programar la configuración; vuelva a intentar"
            )

    def capture(self, shape, color, session):
        camera = self.camera
        self.job(
            lambda: self._capture_now(shape, color, session, expected_camera=camera)
        )

    def capture_guard(self):
        if self.closing.is_set() or self.reconfiguring or self.lifecycle_failed:
            raise PermissionError("Captura cancelada por cierre o reconfiguración")
        if not self.config["simulation"]:
            with self.dispatcher.safety.lock:
                state = self.dispatcher.state
                age = time.monotonic() - self.dispatcher.state_confirmed_at
                if (
                    not self.dispatcher.safety.connected
                    or not 0 <= age <= 0.75
                    or not isinstance(state, dict)
                    or any(
                        state.get(k) is not False
                        for k in (
                            "armed",
                            "motor_activo",
                            "brazo_ocupado",
                            "maintenance",
                        )
                    )
                ):
                    self.burst.cancel.set()
                    raise PermissionError(
                        "Hardware integrado: confirme estado remoto reciente, desarmado y en reposo; desconexión no confirma seguridad"
                    )
        state = self.dispatcher.state or {}
        if (
            state.get("armed")
            or state.get("motor_activo")
            or state.get("brazo_ocupado")
            or self.dispatcher.safety.session
            or self.dispatcher.active
            or not self.dispatcher.queue.empty()
        ):
            self.burst.cancel.set()
            raise PermissionError(
                "Capturar con el robot desarmado y actuadores en reposo"
            )

    def _capture_now(self, shape, color, session, frame=None, expected_camera=None):
        if not self.capture_lock.acquire(blocking=False):
            raise RuntimeError("Ya hay una captura en curso")
        try:
            return self._write_capture(shape, color, session, frame, expected_camera)
        finally:
            self.capture_lock.release()

    def _write_capture(self, shape, color, session, frame, expected_camera):
        if expected_camera is not None and expected_camera is not self.camera:
            raise ValueError("La cámara cambió")
        self.capture_guard()
        snap = self.camera.snapshot()
        if not snap["fresh"]:
            raise ValueError("No hay fotograma fresco")
        frame = frame or snap["frame"]
        if frame.generation != snap["frame"].generation:
            raise ValueError("La sesión de cámara cambió")
        camera = self.camera
        is_burst = (
            self.burst.running and threading.current_thread() is self.burst.thread
        )

        def guard():
            self.capture_guard()
            current = camera.snapshot()
            if (
                camera is not self.camera
                or not current["fresh"]
                or current["frame"].generation != frame.generation
            ):
                raise PermissionError("Captura cancelada: cámara perdida o sustituida")
            if is_burst and self.burst.cancel.is_set():
                raise InterruptedError("Ráfaga cancelada durante almacenamiento")

        path, record = self.dataset.save_record(
            frame, shape, color, session, self.config, guard
        )
        self.event("quality", record["quality"])
        self.event("capture", (path, self.dataset.counts()))

    def start_burst(self, shape, color, session, count=None, interval=None):
        options = self.config["dataset_options"]
        self.burst.start(
            shape,
            color,
            session,
            count if count is not None else options["burst_count"],
            interval if interval is not None else options["burst_interval_s"],
        )

    def record_calibration(self, movement, ms, measurement, unit):
        if movement not in self.config["patterns"]:
            raise ValueError("Movimiento inválido")
        integer(ms, self.config["pulse_min_ms"], self.config["pulse_max_ms"], "ms")
        import math

        if (
            not math.isfinite(measurement)
            or not 0 <= measurement < 10000
            or unit not in ("cm", "grados")
        ):
            raise ValueError("Medición o unidad inválida")

        def task():
            path = ROOT / "calibration" / "mediciones.csv"
            path.parent.mkdir(exist_ok=True)
            new = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                if new:
                    writer.writerow(
                        [
                            "fecha",
                            "movimiento",
                            "pulso_ms",
                            "medicion_humana",
                            "unidad",
                            "modo",
                        ]
                    )
                writer.writerow(
                    [
                        datetime.now().astimezone().isoformat(),
                        movement,
                        ms,
                        measurement,
                        unit,
                        "simulacion" if self.config["simulation"] else "real",
                    ]
                )
            self.event(
                "info", "Medición humana registrada en calibration/mediciones.csv"
            )

        self.job(task)

    def export_logs(self):
        def task():
            import shutil

            target = (
                ROOT
                / "evidencias"
                / ("registros_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            )
            target.mkdir(parents=True, exist_ok=True)
            for source in (ROOT / "logs").glob("robot.log*"):
                shutil.copy2(source, target / source.name)
            self.event("info", "Registros exportados a " + str(target))

        self.job(task)

    def close(self):
        if self.closed:
            return
        self.closing.set()
        if self.dispatcher.safety.connected or self.dispatcher.safety.session:
            self.dispatcher.stop("Cierre de aplicación")
        self.burst.cancel.set()
        try:
            with self.operation_lock:
                try:
                    self.dispatcher.close()
                finally:
                    try:
                        self.burst.stop()
                    finally:
                        try:
                            self.vision.stop()
                        finally:
                            self.camera.stop()
        finally:
            if threading.current_thread() is not self.worker:
                self.worker.join(5)
            self.closed = True
