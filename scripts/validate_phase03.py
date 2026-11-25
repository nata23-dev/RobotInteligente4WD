"""Evidencia reproducible con fixture_prueba; prohíbe red y cámara físicas."""

import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.application import Application
from app.config import defaults
from app.models import Frame
from ai.perception import Perception
from hardware.bridge import HTTPBridge
from hardware.camera import Camera
from ui.main_window import MainWindow
from tests.vision_fixtures import scene
from tests.test_ui_redesign import pump, layout_problems


def benchmark():
    results = []
    for width, height in ((320, 240), (640, 480)):
        p = Perception(defaults()["vision"])
        image = scene(width, height)
        times = []
        cpu_start = time.process_time()
        start = time.perf_counter()
        for i in range(210):
            r = p.process(
                Frame(i, time.monotonic(), image, 0, "benchmark", "fixture_prueba")
            )
            if i >= 10:
                times.append(r.observation.processing_ms)
        wall = time.perf_counter() - start
        results.append(
            {
                "source": "fixture_prueba",
                "resolution": [width, height],
                "samples": 200,
                "mean_ms": float(np.mean(times)),
                "p50_ms": float(np.percentile(times, 50)),
                "p95_ms": float(np.percentile(times, 95)),
                "throughput_fps": 1000 / float(np.mean(times)),
                "cpu_seconds": time.process_time() - cpu_start,
                "wall_s": wall,
            }
        )
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "evidencias/fase03/validacion"
    )
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "fixture_prueba",
        "performance": benchmark(),
        "layouts": [],
        "screenshots": [],
    }
    optional = ROOT / ".tools" / "pdf_deps"
    if optional.exists():
        sys.path.append(str(optional))
    try:
        import psutil

        process = psutil.Process()
        memory = [process.memory_info().rss]
    except ImportError:
        process = None
        memory = []
    with tempfile.TemporaryDirectory() as d, patch(
        "app.application.load", return_value=dict(defaults(), dataset_dir=d)
    ), patch.object(
        HTTPBridge, "request", side_effect=AssertionError("Red física prohibida")
    ), patch.object(
        Camera, "_open", side_effect=AssertionError("Cámara física prohibida")
    ), patch.object(
        socket.socket,
        "connect",
        side_effect=AssertionError("Red prohibida en evidencia"),
    ):
        app = Application(True)
        window = MainWindow(app)
        cancel = threading.Event()
        image = scene()

        def feed():
            identity = 0
            while not cancel.wait(1 / 12):
                identity += 1
                with app.camera.lock:
                    app.camera.latest = Frame(
                        identity,
                        time.monotonic(),
                        image,
                        12,
                        "fixture_session",
                        "fixture_prueba",
                    )
                    app.camera.status = "fixture_prueba"

        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        try:
            window.geometry("1366x697+0+0")
            pump(window, 0.5)
            for mode in ("Original", "Procesada", "Máscara"):
                window.auto.view.set(mode)
                window.auto.select_view()
                pump(window, 0.15)
                name = (
                    "automatico_"
                    + {
                        "Original": "original",
                        "Procesada": "procesada",
                        "Máscara": "mascara",
                    }[mode]
                    + ".png"
                )
                window.screenshot(out / name)
                report["screenshots"].append(name)
            window.auto.expand()
            pump(window, 0.15)
            window.screenshot(out / "automatico_ampliado.png")
            window.auto.expand()
            window.auto.toggle_details()
            pump(window, 0.15)
            window.screenshot(out / "diagnostico.png")
            window.auto.toggle_details()
            window.navigate_config("Visión artificial")
            pump(window, 0.15)
            window.screenshot(out / "configuracion_vision.png")
            page = window.config_tab.pages["Visión artificial"]
            page.canvas.yview_moveto(0.58)
            pump(window, 0.4)
            window.screenshot(out / "calibracion_hsv.png")
            page.canvas.yview_moveto(0)
            window.navigate(2)
            pump(window, 0.15)
            window.screenshot(out / "dataset.png")
            # Ráfaga real del software sobre fixtures, solo en destino temporal.
            app.start_burst("cubo", "rojo", "fixture_session", 10, 0.2)
            for _ in range(65):
                pump(window, 0.05)
                if process:
                    memory.append(process.memory_info().rss)
            report["fixture_capture_count"] = len(
                list(Path(d).rglob("images/**/*.png"))
            )
            report["real_dataset_count"] = sum(app.dataset.counts().values())
            steady = []
            steady_start = time.perf_counter()
            cpu = time.process_time()
            for _ in range(100):
                pump(window, 0.1)
                if process:
                    steady.append(process.memory_info().rss)
            report["steady_rss_bytes"] = steady
            report["steady_cpu_seconds"] = time.process_time() - cpu
            report["steady_wall_s"] = time.perf_counter() - steady_start
            for width, height in (
                (1024, 768),
                (1280, 720),
                (1366, 768),
                (1600, 900),
                (1920, 1080),
            ):
                window.state("normal")
                window.geometry(f"{width}x{height}+0+0")
                pump(window, 0.08)
                for index in range(4):
                    window.navigate(index)
                    pump(window, 0.05)
                    report["layouts"].append(
                        {
                            "requested": [width, height],
                            "actual": [window.winfo_width(), window.winfo_height()],
                            "section": index,
                            "problems": layout_problems(window),
                            "stop_visible": bool(window.stop_button.winfo_ismapped()),
                        }
                    )
            window.geometry("1280x650+0+0")
            window.navigate(0)
            pump(window, 0.1)
            window.state("zoomed")
            pump(window, 0.15)
            report["maximized"] = [window.winfo_width(), window.winfo_height()]
            window.state("normal")
            pump(window, 0.15)
            report["capture_limitations"] = (
                "Monitor físico "
                + str([window.winfo_screenwidth(), window.winfo_screenheight()])
                + ". Capturas inspeccionables dentro de él. 1600/1920 verificados geométricamente; 1024 no admitido, mínimo 1200x650."
            )
            report["vision"] = dict(app.vision.snapshot(), result=None)
            report["requests"] = app.dispatcher.bridge.history
        finally:
            cancel.set()
            feeder.join()
            app.close()
            window.destroy()
    report["rss_bytes_samples"] = memory
    report["rss_delta_bytes"] = memory[-1] - memory[0] if memory else None
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "layouts": len(report["layouts"]),
                "problems": sum(len(x["problems"]) for x in report["layouts"]),
                "performance": report["performance"],
                "real_dataset_count": report["real_dataset_count"],
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
