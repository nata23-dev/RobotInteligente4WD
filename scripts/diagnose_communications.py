"""Diagnóstico local exclusivamente GET; no ejecutar contra hardware sin operador."""

import argparse
import copy
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import load, url
from hardware.bridge import HTTPBridge
from hardware.protocol import validate_health, validate_state
from hardware.telemetry import RecentRequests, error_kind


def local_address(value):
    value = value if "://" in value else "http://" + value
    url(value, "Dirección de diagnóstico", optional=False)
    parts = urlsplit(value)
    if parts.path not in ("", "/"):
        raise ValueError(
            "Indique solo el origen HTTP; el endpoint se selecciona aparte"
        )
    if parts.hostname != "localhost":
        ip = ipaddress.ip_address(parts.hostname)
        if (
            not (ip.is_private or ip.is_loopback)
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("Diagnóstico limitado a direcciones privadas o loopback")
    return value.rstrip("/")


def diagnose(
    config, address, count=200, interval=0.5, timeout=0.3, endpoint="state", cancel=None
):
    from app.vision_config import number

    number(count, 1, 10000, "Cantidad", True)
    number(interval, 0.05, 60, "Intervalo")
    number(timeout, 0.05, 5, "Timeout")
    if endpoint not in ("health", "state"):
        raise ValueError("Solo health o state")
    c = copy.deepcopy(config)
    c.update(robot_url=local_address(address), timeout_s=timeout)
    bridge = HTTPBridge(c, purpose="diagnostic")
    cancel = cancel or threading.Event()
    metrics = RecentRequests()
    records = []
    outages = []
    lost_at = None
    started = time.monotonic()
    try:
        for index in range(count):
            if cancel.is_set():
                break
            start = time.monotonic()
            kind = None
            status = 0
            remote = None
            try:
                result = bridge.request(endpoint)
                (validate_health if endpoint == "health" else validate_state)(result)
                ok = True
                if endpoint == "state":
                    remote = {
                        k: result[k] for k in ("armed", "motor_activo", "brazo_ocupado")
                    }
            except Exception as exc:
                ok = False
                kind = error_kind(exc)
                status = getattr(exc, "status", 0)
            elapsed = time.monotonic() - start
            metrics.record(start, ok, kind)
            if not ok and lost_at is None:
                lost_at = start
            if ok and lost_at is not None:
                outages.append(time.monotonic() - lost_at)
                lost_at = None
            records.append(
                {
                    "query": index + 1,
                    "offset_s": start - started,
                    "ok": ok,
                    "elapsed_ms": elapsed * 1000,
                    "error_type": kind,
                    "http_status": status,
                    "remote": remote,
                }
            )
            if index + 1 < count and cancel.wait(interval):
                break
    except KeyboardInterrupt:
        cancel.set()
    finally:
        bridge.close()
    return {
        "source": (
            "fixture_prueba_loopback"
            if urlsplit(c["robot_url"]).hostname in ("localhost", "127.0.0.1", "::1")
            else "diagnostico_lectura_operador"
        ),
        "endpoint": endpoint,
        "count_requested": count,
        "count_completed": len(records),
        "interval_s": interval,
        "connect_timeout_s": timeout,
        "read_timeout_s": timeout,
        "cancelled": cancel.is_set(),
        "summary": metrics.snapshot(),
        "outages_s": outages,
        "ongoing_outage_s": time.monotonic() - lost_at if lost_at is not None else None,
        "results": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--address", help="Origen HTTP o IP privada, con puerto opcional"
    )
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=0.3)
    parser.add_argument("--endpoint", choices=("health", "state"), default="state")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "evidencias"
        / ("comunicaciones_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"),
    )
    args = parser.parse_args()
    config = load()
    report = diagnose(
        config,
        args.address or config["robot_url"],
        args.count,
        args.interval,
        args.timeout,
        args.endpoint,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "completed": report["count_completed"],
                "summary": report["summary"],
                "output": str(args.output),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
