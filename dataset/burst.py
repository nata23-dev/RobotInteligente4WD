"""Ráfagas cancelables; sin trabajo Tk ni autoridad de movimiento."""

import threading
import time


class Burst:
    def __init__(self, snapshot, capture, safety, event):
        self.snapshot, self.capture, self.safety, self.event = (
            snapshot,
            capture,
            safety,
            event,
        )
        self.cancel = threading.Event()
        self.thread = None
        self.lock = threading.Lock()

    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def start(self, shape, color, session, count=10, interval=1):
        from app.vision_config import number

        number(count, 1, 100, "Cantidad", True)
        number(interval, 0.2, 60, "Intervalo")
        with self.lock:
            if self.running:
                raise RuntimeError("Ya existe una ráfaga activa")
            self.safety()
            if not self.snapshot()["fresh"]:
                raise ValueError("No hay cámara fresca")
            self.cancel.clear()
            self.thread = threading.Thread(
                target=self._run,
                args=(shape, color, session, count, interval),
                name="rafaga",
                daemon=True,
            )
            self.thread.start()

    def stop(self):
        self.cancel.set()
        if self.thread and threading.current_thread() != self.thread:
            self.thread.join(5)
        if self.running:
            raise RuntimeError("La ráfaga no terminó")

    def _run(self, shape, color, session, count, interval):
        saved = 0
        last = None
        generation = None
        reason = "Completada"
        try:
            for index in range(count):
                deadline = time.monotonic() + (interval if index else 0)
                while True:
                    if self.cancel.is_set():
                        raise InterruptedError(
                            "Cancelada por el operador o ciclo de vida"
                        )
                    self.safety()
                    snap = self.snapshot()
                    if not snap["fresh"]:
                        raise ValueError("Pérdida de cámara o fotograma atrasado")
                    frame = snap["frame"]
                    if generation is not None and frame.generation != generation:
                        raise ValueError("Cambio de sesión de cámara")
                    if time.monotonic() >= deadline:
                        break
                    self.cancel.wait(0.03)
                identity = (frame.generation, frame.id)
                if identity == last:
                    raise ValueError("La cámara no proporcionó un fotograma nuevo")
                generation = frame.generation
                last = identity
                self.capture(shape, color, session, frame)
                saved += 1
                self.event(
                    "burst",
                    {
                        "saved": saved,
                        "total": count,
                        "done": False,
                        "reason": "En curso",
                    },
                )
        except Exception as exc:
            reason = str(exc)
        finally:
            self.event(
                "burst",
                {"saved": saved, "total": count, "done": True, "reason": reason},
            )
