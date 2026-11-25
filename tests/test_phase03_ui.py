import gc
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from app.application import Application
from app.config import defaults
from hardware.bridge import HTTPBridge
from hardware.camera import Camera
from app.models import Frame
from ui.main_window import MainWindow
from tests.vision_fixtures import scene
from tests.test_ui_redesign import pump, layout_problems


class Phase03UITests(unittest.TestCase):
    def setUp(self):
        gc.collect()
        self.temp = tempfile.TemporaryDirectory()
        c = defaults()
        c["dataset_dir"] = self.temp.name
        self.patches = [
            patch("app.application.load", return_value=c),
            patch.object(
                HTTPBridge, "request", side_effect=AssertionError("Hardware prohibido")
            ),
            patch.object(
                Camera, "_open", side_effect=AssertionError("Cámara prohibida")
            ),
        ]
        for p in self.patches:
            p.start()
        self.app = Application(True)
        self.window = MainWindow(self.app)
        pump(self.window, 0.15)

    def tearDown(self):
        self.app.close()
        self.window.destroy()
        for p in self.patches:
            p.stop()
        self.temp.cleanup()
        gc.collect()

    def feed(self):
        self.app.camera.latest = Frame(
            1, time.monotonic(), scene(), 12, "fixture_session", "fixture_prueba"
        )
        pump(self.window, 0.16)

    def test_view_modes_actual_results_and_stop_visible(self):
        self.feed()
        w = self.window
        self.assertIsNotNone(self.app.vision.snapshot()["result"])
        for mode in ("Original", "Procesada", "Máscara"):
            w.auto.view.set(mode)
            w.auto.select_view()
            w.auto.update_video(self.app.camera.snapshot())
            self.assertIsNotNone(w.auto.video.photo)
            self.assertTrue(w.stop_button.winfo_ismapped())
        self.assertIn("fixture_prueba", w.auto.video.metrics.get())
        self.assertFalse(self.app.dispatcher.bridge.history)

    def test_enlargement_diagnostics_and_safe_escape(self):
        self.feed()
        w = self.window
        before = w.auto.video.winfo_width()
        w.auto.expand()
        pump(w, 0.04)
        self.assertGreater(w.auto.video.winfo_width(), before)
        self.assertTrue(w.stop_button.winfo_ismapped())
        w.auto.expand()
        w.auto.toggle_details()
        pump(w, 0.04)
        self.assertTrue(w.auto.log.winfo_ismapped())
        self.assertEqual(layout_problems(w), [])
        with patch.object(self.app.dispatcher, "stop") as stopping:
            w.focus_force()
            pump(w, 0.02)
            w.event_generate("<Escape>")
            pump(w, 0.03)
            self.assertGreaterEqual(stopping.call_count, 1)

    def test_config_round_trip_hsv_and_orientation(self):
        form = self.window.config_tab
        form.fields["vision.rotation"].set("90")
        form.fields["vision.hsv.rojo.1.0"].set("165")
        form.fields["vision.grip_roi.0"].set(".2")
        c = form.read()
        self.assertEqual(c["vision"]["rotation"], 90)
        self.assertEqual(c["vision"]["hsv"]["rojo"][1][0], 165)
        form.vision_panel.reset("digital")
        self.assertEqual(
            form.read()["vision"]["digital"], defaults()["vision"]["digital"]
        )

    def test_disconnect_clears_all_views(self):
        self.feed()
        self.app.camera.latest = None
        self.window.auto.update_video(self.app.camera.snapshot())
        self.assertIsNone(self.window.auto.video.photo)
        self.assertIn("Sin observación", self.window.auto.context.get())

    def test_layouts_and_main_stream_single(self):
        w = self.window
        for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
            w.geometry(f"{width}x{height}")
            pump(w, 0.03)
            self.assertEqual((w.winfo_width(), w.winfo_height()), (width, height))
            for index in range(4):
                w.navigate(index)
                pump(w, 0.02)
                self.assertEqual(layout_problems(w), [], (width, height, index))
                self.assertTrue(w.stop_button.winfo_ismapped())
        self.assertIsNone(self.app.camera.thread)
