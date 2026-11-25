"""Ejecuta todas las pruebas con cámara física bloqueada y red solo loopback.

No modifica la configuración local. Requiere las dependencias y el escritorio
gráfico que utiliza la suite Tk existente. Los informes son locales/ignorados.
"""

import argparse
import io
import json
from pathlib import Path
import socket
import sys
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hardware.bridge import HTTPBridge
from hardware.camera import Camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "evidencias/software_checks"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original_connect, original_request = socket.socket.connect, HTTPBridge.request

    def local_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
            raise AssertionError("Red no loopback prohibida durante consolidación")
        return original_connect(sock, address)

    def http_local_only(bridge, action, params=None):
        if urlsplit(bridge.url).hostname not in ("127.0.0.1", "::1"):
            raise AssertionError("HTTP al robot físico prohibido durante consolidación")
        return original_request(bridge, action, params)

    stream = io.StringIO()
    start = time.monotonic()
    with patch.object(socket.socket, "connect", local_only), patch.object(
        HTTPBridge, "request", http_local_only
    ), patch.object(
        Camera, "_open", side_effect=AssertionError("Captura física prohibida")
    ):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    (args.output / "unittest.txt").write_text(stream.getvalue(), encoding="utf-8")
    summary = {
        "executed": result.testsRun,
        "passed": result.testsRun
        - len(result.failures)
        - len(result.errors)
        - len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "elapsed_s": round(elapsed, 3),
        "success": result.wasSuccessful(),
        "network_scope": "solo loopback para pruebas HTTP; cámara física bloqueada",
        "command": "python scripts/check_software.py --output <directorio de evidencias>",
    }
    (args.output / "unittest_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    if not result.wasSuccessful():
        print(stream.getvalue()[-5000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
