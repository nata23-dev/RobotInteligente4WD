"""Métricas acotadas, recientes y sin cuerpos/cabeceras privadas."""

from collections import deque, Counter
import threading
import time
import numpy as np


def error_kind(exc):
    status = getattr(exc, "status", 0)
    if status in (401, 403):
        return "authentication"
    category = getattr(exc, "category", None)
    if category:
        return category
    error = getattr(exc, "error", "")
    if error == "communication_lost":
        return "connection"
    if error in ("robot_url_required", "api_key_required"):
        return "configuration"
    return "protocol"


class RecentRequests:
    def __init__(self, window_s=60):
        self.window_s = window_s
        self.items = deque(maxlen=500)
        self.lock = threading.Lock()
        self.success_total = self.failure_total = self.consecutive = 0
        self.last_valid = None
        self.last_failure = None

    def record(self, start, ok, kind=None):
        now = time.monotonic()
        with self.lock:
            self.items.append((now, (now - start) * 1000, ok, kind))
            if ok:
                self.success_total += 1
                self.consecutive = 0
                self.last_valid = now
            else:
                self.failure_total += 1
                self.consecutive += 1
                self.last_failure = kind

    def snapshot(self):
        now = time.monotonic()
        with self.lock:
            recent = [r for r in self.items if now - r[0] <= self.window_s]
            good = [r[1] for r in recent if r[2]]
            return {
                "p50": float(np.percentile(good, 50)) if good else None,
                "p95": float(np.percentile(good, 95)) if good else None,
                "max": max(good) if good else None,
                "last": recent[-1][1] if recent else None,
                "successes": sum(r[2] for r in recent),
                "errors": sum(not r[2] for r in recent),
                "success_total": self.success_total,
                "failure_total": self.failure_total,
                "consecutive_errors": self.consecutive,
                "last_valid_age_s": (
                    now - self.last_valid if self.last_valid is not None else None
                ),
                "last_failure": self.last_failure,
                "window_s": self.window_s,
                "error_types": dict(Counter(r[3] for r in recent if not r[2])),
            }
