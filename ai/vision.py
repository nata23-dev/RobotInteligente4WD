"""Infraestructura de percepción, sin detección ni navegación autónoma en fase 01."""

import queue
import threading
from dataclasses import replace
import time
from collections import deque
from typing import Protocol
from app.models import Frame, Observation


class Vision(Protocol):
    def process(self, frame: Frame) -> Observation: ...


class LatestObservation:
    """Buzón acotado para el trabajador de percepción de la fase siguiente."""

    def __init__(self):
        self.queue = queue.Queue(maxsize=1)

    def publish(self, observation):
        try:
            self.queue.get_nowait()
        except queue.Empty:
            pass
        self.queue.put_nowait(observation)


class VisionWorker:
    """Un resultado, sin cola de frames; no conoce el despachador."""

    def __init__(self, camera, config, processor=None):
        from ai.perception import Perception

        self.camera = camera
        self.config = config
        self.processor = processor or Perception(config["vision"])
        self.cancel = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.latest = None
        self.errors = 0
        self.times = deque(maxlen=300)
        self.completed = deque(maxlen=120)
        self.revision = 0
        self.pending_profile = None

    def reconfigure(self, profile):
        import copy

        with self.lock:
            self.pending_profile = copy.deepcopy(profile)
            self.revision += 1
            self.latest = None

    def start(self):
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Percepción ya iniciada")
        self.cancel.clear()
        self.thread = threading.Thread(target=self._run, name="percepcion", daemon=True)
        self.thread.start()

    def stop(self):
        self.cancel.set()
        if self.thread:
            self.thread.join(5)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Percepción no terminó")
        with self.lock:
            self.latest = None

    def _run(self):
        previous = None
        while not self.cancel.wait(0.01):
            with self.lock:
                profile = self.pending_profile
                self.pending_profile = None
                revision = self.revision
            if profile is not None:
                from ai.perception import Perception

                self.processor = Perception(profile)
                previous = None
            snap = self.camera.snapshot()
            frame = snap["frame"]
            if not snap["fresh"]:
                with self.lock:
                    self.latest = None
                continue
            identity = (frame.generation, frame.id)
            if identity == previous:
                continue
            previous = identity
            try:
                result = self.processor.process(frame)
                result = replace(
                    result,
                    observation=replace(result.observation, vision_revision=revision),
                )
                current = self.camera.snapshot()
                # Puede publicarse un frame ligeramente anterior al último, pero su
                # imagen y overlays siempre viajan juntos y deben continuar frescos.
                if (
                    self.cancel.is_set()
                    or not current["fresh"]
                    or current["frame"].generation != frame.generation
                    or time.monotonic() - frame.received_at
                    > self.config["frame_max_age_s"]
                ):
                    continue
                with self.lock:
                    if revision != self.revision:
                        continue
                    self.latest = result
                    self.times.append(result.observation.processing_ms)
                    self.completed.append(time.monotonic())
            except Exception:
                with self.lock:
                    self.latest = None
                    self.errors += 1

    def snapshot(self):
        snap = self.camera.snapshot()
        with self.lock:
            result = self.latest
            if result and (
                not snap["fresh"]
                or result.frame.generation != snap["frame"].generation
                or time.monotonic() - result.frame.received_at
                > self.config["frame_max_age_s"]
            ):
                result = None
            fps = (
                (len(self.completed) - 1) / (self.completed[-1] - self.completed[0])
                if len(self.completed) > 1 and self.completed[-1] > self.completed[0]
                else 0.0
            )
            return {
                "result": result,
                "fps": fps,
                "errors": self.errors,
                "times": tuple(self.times),
            }
