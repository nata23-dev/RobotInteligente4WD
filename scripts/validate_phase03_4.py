"""Evidencia Tk real con fixture_prueba; nunca abre cámara ni robot físicos."""

import ctypes
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.application import Application
from app.config import defaults
from app.models import Frame
from hardware.bridge import HTTPBridge
from hardware.camera import Camera
from ui.main_window import MainWindow
from ui.color_calibrator import Calibrator
from ui.dataset_advanced import DatasetAdvanced
from tests.vision_fixtures import scene
from tests.test_ui_redesign import pump, layout_problems


def main():
    out = ROOT / "evidencias/fase03_4R/ui"
    out.mkdir(parents=True, exist_ok=True)
    report = {"source": "fixture_prueba", "layouts": [], "screenshots": []}
    cancel = threading.Event()

    def shot(window, name):
        window.update_idletasks()
        window.lift()
        pump(window, 0.12)
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)
        ImageGrab.grab(window=hwnd).save(out / name)
        report["screenshots"].append(name)

    with tempfile.TemporaryDirectory() as d, patch(
        "app.application.load", return_value=dict(defaults(), dataset_dir=d)
    ), patch.object(
        Camera, "_open", side_effect=AssertionError("Hardware bloqueado")
    ), patch.object(
        HTTPBridge, "request", side_effect=AssertionError("Hardware bloqueado")
    ), patch.object(
        socket.socket, "connect", side_effect=AssertionError("Red bloqueada")
    ):
        app = Application(True)
        window = MainWindow(app)
        image = scene()

        def feed():
            i = 0
            while not cancel.wait(1 / 12):
                i += 1
                with app.camera.lock:
                    app.camera.latest = Frame(
                        i,
                        time.monotonic(),
                        image,
                        12,
                        "fixture_03_4R",
                        "fixture_prueba",
                    )
                    app.camera.status = "fixture_prueba"

        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        try:
            for w, h in ((1280, 720), (1366, 768), (1920, 1080)):
                window.geometry(f"{w}x{h}+0+0")
                pump(window, 0.12)
                for index in range(4):
                    window.navigate(index)
                    pump(window, 0.07)
                    report["layouts"].append(
                        {
                            "requested": [w, h],
                            "actual": [window.winfo_width(), window.winfo_height()],
                            "section": index,
                            "problems": layout_problems(window),
                            "stop_visible": bool(window.stop_button.winfo_ismapped()),
                        }
                    )
            window.geometry("1280x650+0+0")
            window.navigate(0)
            pump(window, 0.3)
            shot(window, "automatico_fixture.png")
            dialog = Calibrator(window, app)
            pump(window, 0.3)
            # Arrastre sobre el rectángulo rojo de la fixture, usando el label real.
            label = dialog.video.label
            dw, dh = label.winfo_width(), label.winfo_height()
            dialog.start_drag(SimpleNamespace(x=int(dw * 0.13), y=int(dh * 0.38)))
            dialog.show_drag(SimpleNamespace(x=int(dw * 0.27), y=int(dh * 0.58)))
            dialog.finish_drag(SimpleNamespace(x=int(dw * 0.27), y=int(dh * 0.58)))
            pump(window, 0.3)
            report["calibrator_sample_count"] = len(dialog.samples)
            report["calibrator_layout"] = layout_problems(dialog.window)
            shot(dialog.window, "calibrador_muestra_fixture.png")
            dialog.close()
            window.navigate(1)
            pump(window, 0.15)
            window.manual.base_dialog()
            pump(window, 0.15)
            manual = window.manual.winfo_children()[-1]
            # Buscar exclusivamente el diálogo Toplevel creado por el control.
            for child in window.manual.winfo_children():
                if child.winfo_class() == "Toplevel":
                    manual = child
            report["manual_dialog_layout"] = layout_problems(manual)
            shot(manual, "base_objetivo_local.png")
            manual.destroy()
            window.navigate(2)
            advanced = DatasetAdvanced(window.dataset)
            pump(window, 0.3)
            shot(advanced.window, "dataset_cobertura_fixture.png")
            advanced.close()
            window.navigate(0)
            window.auto.view.set("Procesada")
            window.auto.select_view()
            report["live_performance"] = []
            optional = ROOT / ".tools/pdf_deps"
            if optional.exists():
                sys.path.append(str(optional))
            try:
                import psutil

                process = psutil.Process()
            except ImportError:
                process = None
            for width, height in ((320, 240), (640, 480)):
                image = scene(width, height)
                pump(window, 0.4)
                received = set()
                processed = set()
                presented = set()
                rss = []
                times = []
                started = time.perf_counter()
                cpu_started = time.process_time()
                for _ in range(80):
                    pump(window, 0.05)
                    snap = app.camera.snapshot()
                    v = app.vision.snapshot()
                    r = v["result"]
                    if snap["frame"]:
                        received.add(snap["frame"].id)
                    if r and r.frame.id not in processed:
                        processed.add(r.frame.id)
                        times.append(r.observation.processing_ms)
                    if window.auto.video.last:
                        presented.add(window.auto.video.last[:2])
                    if process:
                        rss.append(process.memory_info().rss)
                elapsed = time.perf_counter() - started
                import numpy as np

                report["live_performance"].append(
                    {
                        "resolution": [width, height],
                        "wall_s": elapsed,
                        "cpu_s": time.process_time() - cpu_started,
                        "received_observed_fps": len(received) / elapsed,
                        "processed_observed_fps": len(processed) / elapsed,
                        "presented_observed_fps": len(presented) / elapsed,
                        "p50_ms": float(np.percentile(times, 50)) if times else None,
                        "p95_ms": float(np.percentile(times, 95)) if times else None,
                        "rss_min": min(rss) if rss else None,
                        "rss_max": max(rss) if rss else None,
                        "note": "Conteo observado de identidades distintas; muestreo de UI cada 50 ms, fuente sintética nominal 12 FPS.",
                    }
                )
            report["requests"] = app.dispatcher.bridge.history
            report["camera_workers"] = (
                int(bool(app.camera.thread and app.camera.thread.is_alive()))
                if hasattr(app.camera, "thread")
                else 0
            )
            report["monitor"] = [
                window.winfo_screenwidth(),
                window.winfo_screenheight(),
            ]
            report["limit"] = (
                "Capturas de ventanas Tk reales con fixtures. 1920 se comprueba por geometría, fuera del área completa del monitor físico. Sin validación física."
            )
        finally:
            cancel.set()
            feeder.join()
            app.close()
            window.destroy()
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
