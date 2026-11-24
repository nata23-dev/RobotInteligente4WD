"""Evidencia y auditoría geométrica ampliada. Siempre simulación, sin tocar hardware."""

import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.application import Application
from app.config import defaults
from hardware.bridge import HTTPBridge
from ui.main_window import MainWindow
from tests.test_ui_redesign import pump, layout_problems


def main():
    output = Path("evidencias/ui_fase01_1")
    output.mkdir(parents=True, exist_ok=True)
    results = {"simulation_only": True, "layouts": [], "screenshots": []}
    with patch("app.application.load", return_value=defaults()), patch.object(
        HTTPBridge, "request", side_effect=AssertionError("Prohibida red real")
    ):
        app = Application(simulation=True)
        window = MainWindow(app)
        try:
            pump(window)
            results["screen"] = [
                window.winfo_screenwidth(),
                window.winfo_screenheight(),
            ]
            results["tk_scaling"] = float(window.tk.call("tk", "scaling"))
            assert not app.dispatcher.bridge.history
            for index in range(4):
                window.navigate(index)
                pump(window, 0.12)
                results["layouts"].append(
                    {
                        "requested": "ventana inicial",
                        "section": index,
                        "problems": layout_problems(window),
                    }
                )
            window.geometry("1280x650+0+0")
            pump(window, 0.15)
            for index in range(4):
                window.navigate(index)
                pump(window, 0.12)
                results["layouts"].append(
                    {
                        "requested": "área útil compacta 1280×650",
                        "section": index,
                        "problems": layout_problems(window),
                    }
                )
            for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
                window.state("normal")
                window.geometry(f"{width}x{height}+0+0")
                pump(window, 0.15)
                assert (window.winfo_width(), window.winfo_height()) == (
                    width,
                    height,
                ), "El sistema limitó la geometría solicitada"
                for index in range(4):
                    window.navigate(index)
                    pump(window, 0.12)
                    problems = layout_problems(window)
                    results["layouts"].append(
                        {
                            "requested": [width, height],
                            "actual_client": [
                                window.winfo_width(),
                                window.winfo_height(),
                            ],
                            "section": index,
                            "problems": problems,
                            "stop_visible": bool(window.stop_button.winfo_ismapped()),
                        }
                    )
            results["capture_limitations"] = (
                "1600×900 y 1920×1080: comprobación geométrica. El capturador no dibuja las zonas fuera del monitor físico; no se entregan imágenes incompletas."
            )
            # Evidencia física: ventana maximizada dentro del monitor real y su área de trabajo.
            window.state("zoomed")
            pump(window, 0.2)
            for index in range(4):
                window.navigate(index)
                pump(window, 0.3)
                name = f'{index}_{("automatico","manual","dataset","configuracion")[index]}_1366.png'
                window.screenshot(output / name)
                results["screenshots"].append(name)
                results["layouts"].append(
                    {
                        "requested": "monitor real maximizado",
                        "section": index,
                        "actual_client": [window.winfo_width(), window.winfo_height()],
                        "problems": layout_problems(window),
                    }
                )
            # Siete formularios: se permiten desplazamientos intencionales dentro de Configuración.
            for category in window.config_tab.pages:
                window.config_tab.select_category(category)
                pump(window, 0.1)
                results["layouts"].append(
                    {"category": category, "problems": layout_problems(window)}
                )
            # Escala de fuentes virtual: no se modifica la configuración de pantalla Windows.
            base_scale = float(window.tk.call("tk", "scaling"))
            results["virtual_scaling"] = []
            for percent in (125, 150):
                window.tk.call("tk", "scaling", (96 / 72) * percent / 100)
                window.state("normal")
                window.geometry("1920x1080+0+0")
                pump(window, 0.15)
                for index in range(4):
                    window.navigate(index)
                    pump(window, 0.1)
                    results["virtual_scaling"].append(
                        {
                            "percent": percent,
                            "size": [1920, 1080],
                            "section": index,
                            "problems": layout_problems(window),
                        }
                    )
            window.tk.call("tk", "scaling", base_scale)
            window.navigate(1)
            pump(window, 0.1)
            app.command("verify")
            pump(window, 0.3)
            app.command("arm")
            pump(window, 0.2)
            assert app.dispatcher.safety.session
            start = time.monotonic()
            pump(window, 1.0)
            assert (
                app.dispatcher.safety.session
            ), "UI no mantuvo saludable el controlador"
            begin = time.monotonic()
            window.stop_button.invoke()
            pump(window, 0.05)
            assert not app.dispatcher.safety.session
            assert not app.dispatcher.bridge.request("state")["armed"]
            results["simulated_ui_stop_observed_ms"] = (time.monotonic() - begin) * 1000
            results["simulated_heartbeat_ui_healthy_s"] = time.monotonic() - start
            results["problem_count"] = sum(
                len(item["problems"]) for item in results["layouts"]
            )
            results["problem_count"] += sum(
                len(item["problems"]) for item in results["virtual_scaling"]
            )
            (output / "validacion_geometria.json").write_text(
                json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(json.dumps(results, indent=2, ensure_ascii=False))
            assert (
                results["problem_count"] == 0
            ), "Hay recortes de widgets; revisar evidencia JSON"
        finally:
            app.close()
            window.destroy()


if __name__ == "__main__":
    main()
