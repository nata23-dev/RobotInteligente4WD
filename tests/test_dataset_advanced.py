import csv
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from app.application import Application
from app.config import defaults
from app.models import Frame
from dataset.capture import DatasetCapture
from dataset.burst import Burst
from dataset.quality import measure
from dataset.tools import split_sessions, review
from tests.vision_fixtures import scene
from tests.test_dispatcher import until


def fixture(identity=1):
    return Frame(
        identity, time.monotonic(), scene(), 12, "fixture_session", "fixture_prueba"
    )


class AdvancedDatasetTests(unittest.TestCase):
    def test_original_crop_metadata_and_legacy(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            config = defaults()
            f = fixture()
            old = c.save(f, "cubo", "rojo", "old", source="fixture_prueba")
            manifest = Path(d) / "metadata" / "manifest.csv"
            before = manifest.read_bytes()
            path, r = c.save_record(f, "cubo", "rojo", "new", config)
            self.assertTrue(manifest.read_bytes().startswith(before))
            np.testing.assert_array_equal(cv2.imread(str(path)), f.image)
            self.assertEqual(r["source"], "fixture_prueba")
            self.assertEqual(r["frame_id"], f.id)
            self.assertEqual(r["review"], "sin_revisar")
            self.assertEqual(c.counts()["cubo"], 0)
            crop = cv2.imread(str(Path(d) / r["crop"]))
            x1, y1, x2, y2 = r["roi"]
            np.testing.assert_array_equal(crop, f.image[y1:y2, x1:x2])
            self.assertEqual(review(d)[0]["original"], r["original"])

    def test_duplicates_warning_optional_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            config = defaults()
            f = fixture()
            c.save_record(f, "cubo", "rojo", "s", config)
            _, r = c.save_record(f, "cubo", "rojo", "s", config)
            self.assertTrue(r["quality"]["exact_duplicate"])
            config["dataset_options"]["reject_exact_duplicates"] = True
            with self.assertRaises(ValueError):
                c.save_record(f, "cubo", "rojo", "s", config)
            self.assertEqual(len(review(d)), 2)

    def test_quality_dark_bright_blur_and_small(self):
        c = defaults()["dataset_options"]
        for value, word in [(0, "insuficiente"), (255, "excesiva")]:
            r = measure(np.full((20, 20, 3), value, np.uint8), c)
            self.assertIn(word, " ".join(r["warnings"]))
            self.assertEqual(r["sharpness_laplacian"], 0)
            self.assertIn("Resolución", " ".join(r["warnings"]))

    def test_guard_rejects_before_save(self):
        with tempfile.TemporaryDirectory() as d:

            def reject():
                raise PermissionError("Armado durante procesamiento")

            with self.assertRaises(PermissionError):
                DatasetCapture(d).save_record(
                    fixture(), "cubo", "rojo", "s", defaults(), reject
                )
            self.assertEqual(list(Path(d).rglob("*.png")), [])

    def test_burst_new_frames_and_progress(self):
        saved = []
        events = []
        counter = [0]

        def snap():
            counter[0] += 1
            return {"fresh": True, "frame": fixture(counter[0])}

        b = Burst(
            snap,
            lambda s, c, session, f: saved.append(f.id),
            lambda: None,
            lambda *e: events.append(e),
        )
        b.start("cubo", "rojo", "s", 3, 0.2)
        until(lambda: not b.running, timeout=2)
        self.assertEqual(len(saved), 3)
        self.assertEqual(len(set(saved)), 3)
        self.assertTrue(events[-1][1]["done"])

    def test_burst_cancellation_and_no_repeated_frame(self):
        f = fixture()
        events = []
        saved = []
        b = Burst(
            lambda: {"fresh": True, "frame": f},
            lambda *args: saved.append(1),
            lambda: None,
            lambda *e: events.append(e),
        )
        b.start("cubo", "rojo", "s", 3, 0.2)
        until(lambda: not b.running, timeout=2)
        self.assertEqual(len(saved), 1)
        self.assertIn("nuevo", events[-1][1]["reason"])
        b.start("cubo", "rojo", "s", 3, 1)
        b.stop()
        self.assertFalse(b.running)

    def test_burst_safety_each_interval(self):
        safe = [True]
        events = []
        saved = []

        def guard():
            if not safe[0]:
                raise PermissionError("Armado o movimiento")

        b = Burst(
            lambda: {"fresh": True, "frame": fixture()},
            lambda *a: (saved.append(1), safe.__setitem__(0, False)),
            guard,
            lambda *e: events.append(e),
        )
        b.start("cubo", "rojo", "s", 3, 0.2)
        until(lambda: not b.running)
        self.assertEqual(len(saved), 1)
        self.assertIn("Armado", events[-1][1]["reason"])

    def test_application_rejects_remote_arm_motion_and_close(self):
        with patch("app.application.load", return_value=defaults()):
            app = Application(True)
        try:
            for key in ("armed", "motor_activo", "brazo_ocupado"):
                app.dispatcher.state = {key: True}
                with self.assertRaises(PermissionError):
                    app.capture_guard()
            app.dispatcher.state = {}
            app.reconfiguring = True
            with self.assertRaises(PermissionError):
                app.capture_guard()
        finally:
            app.close()
        self.assertFalse(app.vision.thread.is_alive())

    def test_capture_mutex_rejects_arm_without_blocking_stop(self):
        with patch('app.application.load',return_value=defaults()):app=Application(True)
        try:
            app.capture_lock.acquire()
            app.command('arm')
            self.assertEqual(app.dispatcher.bridge.history,[])
            # STOP no adquiere el mutex de captura ni espera a la codificación.
            started=time.monotonic();app.dispatcher.stop()
            self.assertLess(time.monotonic()-started,.2)
            self.assertFalse(app.dispatcher.safety.session)
        finally:
            app.capture_lock.release();app.close()

    def test_burst_loss_staleness_generation_and_cancel(self):
        for mode in ('loss','stale','generation'):
            events=[];saved=[];active=[False]
            def snap():
                f=fixture()
                if active[0] and mode=='generation':f=Frame(f.id,f.received_at,f.image,12,'different','fixture_prueba')
                return {'fresh':not active[0] or mode=='generation','frame':f}
            def capture(*args):saved.append(1);active[0]=True
            b=Burst(snap,capture,lambda:None,lambda *e:events.append(e))
            b.start('cubo','rojo','s',3,.2);until(lambda:not b.running)
            self.assertEqual(len(saved),1,mode)
            self.assertNotEqual(events[-1][1]['reason'],'Completada')

    def test_split_sessions_whole_and_insufficient(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "metadata").mkdir()
            (root / "images").mkdir()
            with self.assertRaises(ValueError):
                split_sessions(root)
            rows = []
            for session in range(8):
                for shape in ("cubo", "cilindro", "prisma_triangular"):
                    path = f"images/{session}_{shape}.png"
                    (root / path).write_bytes(b"fixture_prueba_imported_manifest")
                    rows.append(
                        {
                            "image": path,
                            "shape": shape,
                            "color": "rojo",
                            "session": f"s{session}",
                            "source": "camara_real",
                        }
                    )
            with (root / "metadata" / "manifest.csv").open(
                "w", newline="", encoding="utf-8"
            ) as s:
                writer = csv.DictWriter(s, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            result = split_sessions(root)
            for session in result["sessions"]:
                self.assertEqual(
                    len(
                        {
                            r["subset"]
                            for r in result["items"]
                            if r["session"] == session
                        }
                    ),
                    1,
                )
            self.assertEqual(
                {r["subset"] for r in result["items"]}, {"train", "validation", "test"}
            )
