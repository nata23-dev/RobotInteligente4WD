"""Composición y tareas de disco/ciclo de vida fuera del hilo de Tkinter."""
import copy
import csv
from datetime import datetime
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
import queue
import threading
from app.config import ROOT, LOCAL, load, save, validate, integer
from app.models import Command
from control.command_dispatcher import Dispatcher
from control.controller import Controller
from hardware.bridge import HTTPBridge
from hardware.camera import Camera
from hardware.simulator import Simulator
from dataset.capture import DatasetCapture


def setup_logging():
    (ROOT / 'logs').mkdir(exist_ok=True)
    records = queue.Queue(maxsize=2000)
    handler = RotatingFileHandler(ROOT / 'logs' / 'robot.log', maxBytes=1_000_000,
                                 backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
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
            self.config['simulation'] = simulation
        self.events = queue.Queue(maxsize=100)
        self.jobs = queue.Queue(maxsize=8)
        self.closing = threading.Event()
        self.operation_lock = threading.Lock()
        self.reconfiguring = False
        self.closed = False
        self.close_error = None
        self._compose()
        self.worker = threading.Thread(target=self._jobs, name='archivos-y-ciclo', daemon=True)
        self.worker.start()

    def _compose(self):
        c = copy.deepcopy(self.config)
        if c['simulation']:
            bridge = stop_bridge = Simulator()
        else:
            bridge, stop_bridge = HTTPBridge(c), HTTPBridge(c)
        self.dispatcher = Dispatcher(bridge, stop_bridge, c)
        self.controller = Controller(self.dispatcher)
        self.camera = Camera(c)
        destination = Path(c['dataset_dir'])
        self.dataset = DatasetCapture(destination if destination.is_absolute() else ROOT / destination)
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
            self.event('info', 'Tarea descartada durante cierre o configuración')
            return
        try:
            self.jobs.put_nowait(fn)
        except queue.Full:
            self.event('error', 'Hay demasiadas tareas pendientes')

    def _jobs(self):
        while not self.closing.is_set():
            try:
                fn = self.jobs.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                with self.operation_lock:
                    if not self.closing.is_set():
                        fn()
            except Exception as exc:
                self.event('error', str(exc))

    def command(self, action, params=None):
        if self.reconfiguring or self.closing.is_set():
            self.event('error', 'Aplicación cambiando configuración o cerrando')
            return
        future = self.dispatcher.submit(Command(action, params or {}))
        def done(f):
            if f.cancelled():
                self.event('info', 'Orden cancelada por seguridad')
                return
            try:
                f.result()
                self.event('info', action + ': completado (respuesta lógica)')
            except Exception as exc:
                self.event('error', str(exc))
        future.add_done_callback(done)

    def update_config(self, config):
        new = validate(config)
        with self.dispatcher.safety.lock:
            if self.dispatcher.safety.session or self.dispatcher.state.get('armed'):
                raise PermissionError('Detenga el robot y confirme estado desarmado antes de configurar')
            if self.dispatcher.active or not self.dispatcher.queue.empty() or self.reconfiguring:
                raise PermissionError('Espere a que terminen las tareas pendientes')
            self.reconfiguring = True
            self.dispatcher.safety.invalidate('Cambio de configuración')
        def apply():
            previous = self.config
            try:
                self.camera.stop()
                self.dispatcher.close()
                if self.dispatcher.safety.status.startswith('Parada no confirmada'):
                    raise PermissionError('Confirme la parada con el equipo anterior antes de cambiar configuración')
                save(new)
                self.config = new
                self._compose()
                self.event('configured', 'Configuración guardada. Conexión y armado explícitos requeridos.')
            except Exception:
                if not self.dispatcher.worker.is_alive():
                    self.config = previous
                    self._compose()
                raise
            finally:
                self.reconfiguring = False
        self.job(apply, internal=True)

    def capture(self, shape, color, session):
        camera = self.camera
        dataset = self.dataset
        def task():
            snap = camera.snapshot()
            if not snap['fresh']:
                raise ValueError('No hay fotograma fresco de la cámara real')
            state = self.dispatcher.state
            if state.get('motor_activo') or state.get('brazo_ocupado') or self.dispatcher.safety.session:
                raise PermissionError('Capturar con el robot desarmado y actuadores en reposo')
            path = dataset.save(snap['frame'], shape, color, session,
                                max_age=self.config['frame_max_age_s'])
            self.event('capture', (path, dataset.counts()))
        self.job(task)

    def record_calibration(self, movement, ms, measurement, unit):
        if movement not in self.config['patterns']:
            raise ValueError('Movimiento inválido')
        integer(ms, self.config['pulse_min_ms'], self.config['pulse_max_ms'], 'ms')
        import math
        if not math.isfinite(measurement) or not 0 <= measurement < 10000 or unit not in ('cm', 'grados'):
            raise ValueError('Medición o unidad inválida')
        def task():
            path = ROOT / 'calibration' / 'mediciones.csv'
            path.parent.mkdir(exist_ok=True)
            new = not path.exists()
            with path.open('a', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                if new:
                    writer.writerow(['fecha', 'movimiento', 'pulso_ms', 'medicion_humana', 'unidad', 'modo'])
                writer.writerow([datetime.now().astimezone().isoformat(), movement, ms, measurement, unit,
                                 'simulacion' if self.config['simulation'] else 'real'])
            self.event('info', 'Medición humana registrada en calibration/mediciones.csv')
        self.job(task)

    def export_logs(self):
        def task():
            import shutil
            target = ROOT / 'evidencias' / ('registros_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            target.mkdir(parents=True, exist_ok=True)
            for source in (ROOT / 'logs').glob('robot.log*'):
                shutil.copy2(source, target / source.name)
            self.event('info', 'Registros exportados a ' + str(target))
        self.job(task)

    def close(self):
        if self.closed:
            return
        self.closing.set()
        try:
            with self.operation_lock:
                try:
                    self.dispatcher.close()
                finally:
                    self.camera.stop()
        finally:
            if threading.current_thread() is not self.worker:
                self.worker.join(5)
            self.closed = True
