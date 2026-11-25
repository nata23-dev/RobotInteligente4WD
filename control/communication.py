"""Disponibilidad y recuperación; nunca concede sesiones de movimiento."""

from collections import deque
import threading
import time
from hardware.telemetry import RecentRequests

RETRY_DELAYS = (0.5, 1.0, 2.0, 3.0)
STATE_MAX_AGE_S = 0.75
HEARTBEAT_CONFIRMATION_LIMIT_S = 0.75


class Communication:
    def __init__(self):
        self.lock = threading.RLock()
        self.requests = RecentRequests()
        self.state = "Sin verificar"
        self.stop_state = "Sin solicitar"
        self.last_failure = None
        self.consecutive = 0
        self.reconnections = 0
        self.outage_started = None
        self.last_outage_s = None
        self.outages = deque(maxlen=100)
        self.events = deque(maxlen=100)
        self.recovered_at = 0.0

    def set_state(self, state):
        with self.lock:
            if self.state != state:
                self.state = state
                self.events.append((time.monotonic(), state))

    def failed(self, kind):
        with self.lock:
            self.last_failure = kind
            self.consecutive += 1
            if self.outage_started is None:
                self.outage_started = time.monotonic()
            self.set_state(
                "Conexión inestable"
                if self.consecutive == 1
                else "Comunicación perdida"
            )

    def recovered(self):
        with self.lock:
            if self.outage_started is not None:
                self.last_outage_s = time.monotonic() - self.outage_started
                self.outages.append(self.last_outage_s)
                self.reconnections += 1
                self.outage_started = None
                self.recovered_at = time.monotonic()
                self.set_state("Conexión recuperada / desarmado")
            elif time.monotonic() - self.recovered_at > 3:
                self.set_state("Conectado")
            self.consecutive = 0

    def snapshot(self):
        with self.lock:
            metrics = self.requests.snapshot()
            return dict(
                metrics,
                state=self.state,
                stop_state=self.stop_state,
                consecutive_request_errors=metrics["consecutive_errors"],
                last_failure=self.last_failure,
                consecutive_errors=self.consecutive,
                reconnections=self.reconnections,
                last_outage_s=self.last_outage_s,
                current_outage_s=(
                    time.monotonic() - self.outage_started
                    if self.outage_started is not None
                    else None
                ),
                recent_outages_s=tuple(self.outages),
                events=tuple(self.events),
            )
