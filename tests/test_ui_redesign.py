"""Regresiones UX verificadas con Tk real y hardware físico expresamente bloqueado."""

import csv
import gc
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch
from PIL import Image
from app.application import Application
from app.config import defaults, save, load
from hardware.bridge import HTTPBridge
from ui.main_window import MainWindow
from ui.dataset_view import dataset_summary
from ui.preferences import load_goal, save_goal
from ui import theme
from app.models import Frame
import numpy as np


def pump(window, seconds=0.15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        window.update()
        time.sleep(0.005)


def layout_problems(parent):
    """Detecta recorte vertical/horizontal, incluido texto reducido por el layout."""
    problems = []
    for child in parent.winfo_children():
        if not child.winfo_ismapped():
            continue
        manager = child.winfo_manager()
        if manager in ("pack", "grid", "place"):
            x, y, w, h = (
                child.winfo_x(),
                child.winfo_y(),
                child.winfo_width(),
                child.winfo_height(),
            )
            if (
                x < -2
                or y < -2
                or x + w > parent.winfo_width() + 2
                or y + h > parent.winfo_height() + 2
            ):
                problems.append(
                    (
                        str(child),
                        "fuera de contenedor",
                        (x, y, w, h),
                        (parent.winfo_width(), parent.winfo_height()),
                    )
                )
            if (
                child.winfo_class()
                in ("TButton", "TLabel", "Label", "TEntry", "TSpinbox", "TCombobox")
                and h < child.winfo_reqheight() - 2
            ):
                problems.append(
                    (str(child), "altura recortada", h, child.winfo_reqheight())
                )
        problems.extend(layout_problems(child))
    return problems


class UIIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Tk necesita destruir sus objetos en el hilo principal. Recoger las
        # ventanas de pruebas anteriores antes de iniciar nuevos trabajadores.
        gc.collect()
        self.temp = tempfile.TemporaryDirectory()
        config = defaults()
        config["dataset_dir"] = self.temp.name
        self.loading = patch("app.application.load", return_value=config)
        self.loading.start()
        self.network = patch.object(
            HTTPBridge,
            "request",
            side_effect=AssertionError("Hardware real prohibido en prueba UI"),
        )
        self.network.start()
        self.app = Application(simulation=True)
        self.window = MainWindow(self.app)
        pump(self.window)

    def tearDown(self):
        self.app.close()
        self.window.destroy()
        self.loading.stop()
        self.network.stop()
        self.temp.cleanup()
        gc.collect()

    def test_start_navigation_and_pending_states(self):
        w = self.window
        self.assertEqual(w.tabs.index("current"), 0)
        self.assertEqual(w.tabs.index("end"), 4)
        self.assertEqual(self.app.dispatcher.bridge.history, [])
        self.assertIn("disabled", w.auto.start.state())
        self.assertIn("disabled", w.auto.pause.state())
        self.assertIn("disabled", w.dataset.burst.state())
        for index in (1, 2, 3, 0):
            w.navigate(index)
            pump(w, 0.03)
            self.assertTrue(w.stop_button.winfo_ismapped())
        self.assertEqual(self.app.dispatcher.bridge.history, [])

    def test_forms_round_trip_and_password_mask(self):
        form = self.window.config_tab
        self.assertEqual(form.read(), self.app.config)
        self.assertEqual(form.form_widgets["api_key"].cget("show"), "●")
        form.fields["pulse_ms"].set("200")
        form.fields["api_key"].set("fixture-api-key-sin-valor-real")
        target = Path(self.temp.name) / "config.local.json"
        with patch("app.application.save", side_effect=lambda c: save(c, target)):
            form.save()
            end = time.monotonic() + 2
            while self.app.reconfiguring and time.monotonic() < end:
                pump(self.window, 0.03)
        self.assertEqual(load(target)["pulse_ms"], 200)
        self.assertEqual(form.key.get(), "fixture-api-key-sin-valor-real")
        self.assertFalse(self.app.dispatcher.safety.session)
        self.assertFalse(self.app.dispatcher.safety.connected)

    def test_invalid_forms_do_not_apply(self):
        form = self.window.config_tab
        form.fields["pulse_max_ms"].set("701")
        with self.assertRaises(ValueError):
            form.save()
        self.assertEqual(self.app.config["pulse_max_ms"], 700)
        self.assertEqual(self.app.dispatcher.bridge.history, [])

    def test_patterns_swap_preserves_unsaved_fields(self):
        form = self.window.config_tab
        form.fields["robot_url"].set("http://fixture.local")
        before = form.read()["patterns"]
        form.swap()
        after = form.read()
        self.assertEqual(after["patterns"]["izquierda"], before["derecha"])
        self.assertEqual(after["patterns"]["derecha"], before["izquierda"])
        self.assertEqual(after["robot_url"], "http://fixture.local")

    def test_confirmation_cannot_release_without_approval(self):
        self.window.navigate(1)
        pump(self.window)
        with patch("ui.tabs.manual.confirm", return_value=False):
            self.window.manual.release("garra")
            self.window.manual.enable("base")
        self.assertEqual(self.app.dispatcher.bridge.history, [])

    def test_global_stop_and_mode_change_in_simulator(self):
        w = self.window
        w.navigate(1)
        pump(w)
        self.app.command("verify")
        pump(w, 0.2)
        self.app.command("arm")
        pump(w, 0.12)
        self.assertTrue(self.app.dispatcher.safety.session)
        w.config_tab.fields["pulse_ms"].set("200")
        with self.assertRaises(PermissionError):
            w.config_tab.save()
        w.stop_button.invoke()
        pump(w, 0.12)
        self.assertFalse(self.app.dispatcher.safety.session)
        self.assertFalse(self.app.dispatcher.bridge.request("state")["armed"])
        self.app.command("arm")
        pump(w, 0.12)
        self.assertTrue(self.app.dispatcher.safety.session)
        w.navigate(2)
        pump(w, 0.12)
        self.assertFalse(self.app.dispatcher.safety.session)
        self.assertFalse(self.app.dispatcher.bridge.request("state")["armed"])

    def test_original_processed_selector_does_not_invent_image(self):
        video = self.window.auto.video
        self.window.auto.view.set("Procesada · pendiente")
        self.window.auto.select_view()
        video.update_frame(self.app.camera.snapshot())
        self.assertIsNone(video.photo)
        self.assertEqual(video.empty_title.cget("text"), "Procesamiento pendiente")

    def test_video_keeps_original_aspect_ratio(self):
        # Fixture en memoria: no se guarda ni se presenta como cámara física.
        video = self.window.auto.video
        frame = Frame(1, time.monotonic(), np.zeros((100, 200, 3), np.uint8), 12.0)
        video.update_frame(
            {"frame": frame, "fresh": True, "age_s": 0.0, "status": "fixture de prueba"}
        )
        self.assertIsNotNone(video.photo)
        self.assertAlmostEqual(
            video.photo.width() / video.photo.height(), 2.0, delta=0.02
        )

    def test_initial_and_compact_layout_with_saved_preview(self):
        w = self.window
        self.assertEqual(layout_problems(w), [])
        # Solo una miniatura de prueba en memoria; nunca se guarda en el dataset.
        summary = {
            "root": self.app.dataset.root.resolve(),
            "shapes": {"cubo": 0, "cilindro": 0, "prisma_triangular": 0},
            "colors": {"rojo": 0, "verde": 0, "azul": 0},
            "total": 0,
            "latest": None,
            "preview": Image.new("RGB", (120, 40)),
        }
        w.dataset.apply_summary(summary)
        w.geometry("1280x650")
        pump(w)
        for index in range(4):
            w.navigate(index)
            pump(w, 0.04)
            self.assertEqual(layout_problems(w), [], index)


class PresentationDataTests(unittest.TestCase):
    def test_real_manifest_counts_without_fixtures_duplicates_or_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata").mkdir()
            (root / "images").mkdir()
            Image.new("RGB", (4, 4)).save(root / "images" / "original.png")
            Image.new("RGB", (4, 4)).save(root / "images" / "fixture.png")
            fields = ("image", "shape", "color", "source")
            with (root / "metadata" / "manifest.csv").open(
                "w", newline="", encoding="utf-8"
            ) as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                row = dict(
                    zip(fields, ["images/original.png", "cubo", "rojo", "camara_real"])
                )
                writer.writerow(row)
                writer.writerow(row)
                writer.writerow(
                    dict(
                        zip(
                            fields,
                            [
                                "images/fixture.png",
                                "cilindro",
                                "azul",
                                "fixture_prueba",
                            ],
                        )
                    )
                )
                writer.writerow(
                    dict(
                        zip(
                            fields,
                            ["images/ausente.png", "cilindro", "azul", "camara_real"],
                        )
                    )
                )
            data = dataset_summary(root)
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["colors"], {"rojo": 1, "verde": 0, "azul": 0})
            self.assertEqual(data["shapes"]["cubo"], 1)
            self.assertIsNotNone(data["preview"])

    def test_dataset_goal_persistence_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "ui.local.json"
            self.assertEqual(load_goal(p), 150)
            save_goal(200, p)
            self.assertEqual(load_goal(p), 200)
            with self.assertRaises(ValueError):
                save_goal(0, p)

    def test_legible_text_token_contrast(self):
        def luminance(color):
            channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [
                c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                for c in channels
            ]
            return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))

        for fg, bg in [
            ("text_primary", "surface"),
            ("text_secondary", "surface"),
            ("primary", "surface"),
            ("warning_text", "warning_soft"),
            ("success_text", "success_soft"),
            ("muted_text", "background"),
            ("muted_text", "surface_secondary"),
            ("neural_text", "neural_soft"),
            ("danger_text", "danger_soft"),
            ("primary_text", "primary_soft"),
        ]:
            ratio = (
                max(luminance(theme.COLORS[fg]), luminance(theme.COLORS[bg])) + 0.05
            ) / (min(luminance(theme.COLORS[fg]), luminance(theme.COLORS[bg])) + 0.05)
            self.assertGreaterEqual(ratio, 4.5, (fg, bg, ratio))
