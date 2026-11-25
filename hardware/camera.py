"""Captura FFmpeg acotada; un trabajador y un solo fotograma reciente."""
from collections import deque
import threading
import time
import uuid
import cv2
from app.models import Frame


class Camera:
    def __init__(self, config, factory=None):
        self.config = config
        self.factory = factory or self._open
        self.lock = threading.Lock()
        self.lifecycle = threading.Lock()
        self.cancel = threading.Event()
        self.thread = None
        self.latest = None
        self.frame_id = 0
        self.status = 'Desconectada'
        self.errors = 0
        self.generation = uuid.uuid4().hex

    def _open(self, url):
        timeout = self.config['camera_timeout_ms']
        return cv2.VideoCapture(url, cv2.CAP_FFMPEG,
             [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout, cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout])

    def start(self):
        with self.lifecycle:
            if self.thread and self.thread.is_alive():
                raise RuntimeError('La cámara ya tiene un trabajador; detener antes de iniciar')
            if not self.config['camera_url']:
                raise ValueError('Configure la URL real del video')
            self.cancel.clear()
            with self.lock:
                self.latest = None
                self.status = 'Conectando'
            self.thread = threading.Thread(target=self._run, name='camara', daemon=True)
            self.thread.start()

    def stop(self):
        self.cancel.set()
        with self.lifecycle:
            if self.thread:
                self.thread.join((2 * self.config['camera_timeout_ms']) / 1000 + 1)
                if self.thread.is_alive():
                    raise RuntimeError('El backend de cámara sigue bloqueado; reinicio bloqueado')
            with self.lock:
                self.latest = None
                self.status = 'Desconectada'

    def _run(self):
        while not self.cancel.is_set():
            cap = None
            times = deque(maxlen=31)
            try:
                cap = self.factory(self.config['camera_url'])
                if not cap.isOpened():
                    raise OSError('No disponible')
                self.generation = uuid.uuid4().hex
                while not self.cancel.is_set():
                    ok, image = cap.read()
                    if not ok or image is None:
                        raise OSError('Video perdido')
                    now = time.monotonic()
                    times.append(now)
                    fps = (len(times) - 1) / (times[-1] - times[0]) if len(times) > 1 and times[-1] > times[0] else 0.
                    with self.lock:
                        if self.cancel.is_set():
                            break
                        self.frame_id += 1
                        self.latest = Frame(self.frame_id, now, image.copy(), fps, self.generation)
                        self.status = 'Conectada'
            except Exception:
                with self.lock:
                    self.errors += 1
                    self.latest = None
                    self.status = 'Desconectada / esperando reconexión'
            finally:
                if cap is not None:
                    cap.release()
            self.cancel.wait(self.config['camera_retry_s'])

    def snapshot(self):
        with self.lock:
            f = self.latest
            age = time.monotonic() - f.received_at if f else None
            fresh = f is not None and age <= self.config['frame_max_age_s'] and not self.cancel.is_set()
            return {'frame': f, 'fresh': fresh, 'age_s': age,
                    'status': self.status if fresh or not f else 'Video atrasado', 'errors': self.errors}
