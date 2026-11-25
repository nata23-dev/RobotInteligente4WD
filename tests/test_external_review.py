"""Regresiones 03.1-R: fixtures, fallos de almacenamiento y carreras sin hardware."""

import copy
import gc
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from app.application import Application
from app.config import defaults, ROOT
from app.models import Frame, Command
from dataset.capture import DatasetCapture
from dataset.tools import review, set_review, split_sessions
from dataset import storage
from tests.vision_fixtures import scene
from tests.test_dispatcher import until
from tests.test_ui_redesign import pump
from hardware.bridge import HTTPBridge
from ui.main_window import MainWindow


def fixture(identity=1):
    return Frame(
        identity, time.monotonic(), scene(), 12, "review_fixture", "fixture_prueba"
    )


class CaptureTransactionTests(unittest.TestCase):
    def test_failures_png_manifest_crop_jsonl_restore_previous(self):
        for component in ("original", "manifest", "crop", "jsonl"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as d:
                dataset = DatasetCapture(d)
                c = defaults()
                c["frame_max_age_s"] = 5
                dataset.save_record(fixture(), "cubo", "rojo", "existing", c)
                snapshot = {
                    p.relative_to(d).as_posix(): p.read_bytes()
                    for p in Path(d).rglob("*")
                    if p.is_file()
                }
                original = storage.atomic_bytes
                failed = []

                def broken(path, data):
                    path = Path(path)
                    match = {
                        "original": "images" in path.parts,
                        "manifest": path.name == "manifest.csv",
                        "crop": "derived" in path.parts,
                        "jsonl": path.name == "vision_v2.jsonl",
                    }[component]
                    if match and not failed:
                        failed.append(True)
                        original(
                            path, data
                        )  # Incluso tras reemplazo exitoso, simular fallo posterior.
                        raise OSError("Fallo inyectado " + component)
                    return original(path, data)

                with patch.object(storage, "atomic_bytes", broken), self.assertRaises(
                    OSError
                ):
                    dataset.save_record(fixture(2), "cubo", "rojo", "new", c)
                after = {
                    p.relative_to(d).as_posix(): p.read_bytes()
                    for p in Path(d).rglob("*")
                    if p.is_file()
                }
                self.assertEqual(snapshot, after)
                self.assertEqual(len(review(d)), 1)

    def test_close_during_storage_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            dataset = DatasetCapture(d)
            closed = threading.Event()
            original = storage.atomic_bytes

            def write(path, data):
                original(path, data)
                if Path(path).name == "manifest.csv":
                    closed.set()

            def guard():
                if closed.is_set():
                    raise InterruptedError("Cierre durante escritura")

            with patch.object(storage, "atomic_bytes", write), self.assertRaises(
                InterruptedError
            ):
                dataset.save_record(fixture(), "cubo", "rojo", "s", defaults(), guard)
            self.assertEqual(list(Path(d).rglob("*.png")), [])
            self.assertFalse((Path(d) / "metadata/manifest.csv").exists())
            self.assertFalse((Path(d) / "metadata/vision_v2.jsonl").exists())

    def test_process_crash_recovers_once_without_duplicate_or_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            DatasetCapture(d).save_record(
                fixture(), "cubo", "rojo", "before", defaults()
            )
            before = {
                p.relative_to(d).as_posix(): p.read_bytes()
                for p in Path(d).rglob("*")
                if p.is_file()
            }
            code = """
import os,sys
from pathlib import Path
from unittest.mock import patch
from dataset import storage
from dataset.capture import DatasetCapture
from tests.test_external_review import fixture
from app.config import defaults
write=storage.atomic_bytes
def crash(path,data):
    write(path,data)
    if Path(path).name=='vision_v2.jsonl':os._exit(73)
with patch.object(storage,'atomic_bytes',crash):
    DatasetCapture(sys.argv[1]).save_record(fixture(2),'cubo','rojo','crash',defaults())
"""
            result = subprocess.run(
                [sys.executable, "-c", code, d],
                cwd=ROOT,
                capture_output=True,
                timeout=15,
            )
            self.assertEqual(
                result.returncode, 73, result.stderr.decode(errors="replace")
            )
            self.assertTrue(list((Path(d) / "metadata/transactions").glob("*.json")))
            DatasetCapture(d)
            DatasetCapture(d)
            after = {
                p.relative_to(d).as_posix(): p.read_bytes()
                for p in Path(d).rglob("*")
                if p.is_file()
            }
            self.assertEqual(before, after)

    def test_ambiguous_same_color_does_not_assign_crop(self):
        with tempfile.TemporaryDirectory() as d:
            image = np.full((240, 320, 3), 230, np.uint8)
            cv2.rectangle(image, (20, 30), (80, 130), (0, 0, 220), -1)
            cv2.rectangle(image, (190, 30), (260, 150), (0, 0, 220), -1)
            f = Frame(1, time.monotonic(), image, 0, "fixture", "fixture_prueba")
            _, record = DatasetCapture(d).save_record(
                f, "cubo", "rojo", "s", defaults()
            )
            self.assertIsNone(record["crop"])
            self.assertIsNone(record["roi"])
            self.assertIn("Varias figuras", " ".join(record["quality"]["warnings"]))


class CaptureAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.loader = patch("app.application.load", return_value=defaults())
        self.loader.start()
        self.app = Application(True)

    def tearDown(self):
        self.app.close()
        self.loader.stop()

    def test_unknown_disconnected_stale_and_known_hardware(self):
        app = self.app
        app.config["simulation"] = False
        d = app.dispatcher
        with self.assertRaises(PermissionError):
            app.capture_guard()
        d.safety.connected = True
        d.state = {
            "armed": False,
            "motor_activo": False,
            "brazo_ocupado": False,
            "maintenance": False,
        }
        with self.assertRaises(PermissionError):
            app.capture_guard()
        d.state_confirmed_at = time.monotonic()
        app.capture_guard()
        d.state_confirmed_at = time.monotonic() - 1
        with self.assertRaises(PermissionError):
            app.capture_guard()
        d.state_confirmed_at = time.monotonic()
        d.safety.connected = False
        with self.assertRaises(PermissionError):
            app.capture_guard()
        d.safety.connected = True
        del d.state["brazo_ocupado"]
        with self.assertRaises(PermissionError):
            app.capture_guard()
        d.state = None
        with self.assertRaises(PermissionError):
            app.capture_guard()

    def test_simulation_explicit_without_remote_state(self):
        self.app.capture_guard()
        self.assertEqual(self.app.dispatcher.bridge.history, [])

    def test_direct_dispatcher_arm_rejected_while_capture_reserved(self):
        app = self.app
        d = app.dispatcher
        app.capture_lock.acquire()
        try:
            future = d.submit(Command("arm"))
            with self.assertRaises(PermissionError):
                future.result(1)
            start = time.monotonic()
            d.stop()
            self.assertLess(time.monotonic() - start, 0.2)
        finally:
            app.capture_lock.release()
        self.assertNotIn("arm", [r[0] for r in d.bridge.history])

    def test_arm_in_flight_prevents_capture(self):
        app = self.app
        d = app.dispatcher
        app.controller.change_mode("manual")
        app.controller.tick()
        d.submit(Command("verify")).result(1)
        original = d.bridge.request
        entered = threading.Event()
        release = threading.Event()

        def request(action, params=None):
            if action == "arm":
                entered.set()
                release.wait(1)
            return original(action, params)

        with patch.object(d.bridge, "request", request):
            future = d.submit(Command("arm"))
            try:
                self.assertTrue(entered.wait(1))
                with self.assertRaises(RuntimeError):
                    app._capture_now("cubo", "rojo", "s")
                with self.assertRaises(PermissionError):
                    app.capture_guard()
            finally:
                release.set()
                future.result(1)

    def test_dequeued_arm_cannot_cross_capture_reservation(self):
        app = self.app
        d = app.dispatcher
        original_get = d.queue.get
        entered = threading.Event()
        release = threading.Event()
        instrumented = threading.Event()

        def get(*args, **kwargs):
            instrumented.set()
            item = original_get(*args, **kwargs)
            if item[2].action == "arm":
                entered.set()
                release.wait(1)
            return item

        with patch.object(d.queue, "get", get):
            self.assertTrue(instrumented.wait(1))
            future = d.submit(Command("arm"))
            try:
                self.assertTrue(entered.wait(1))
                app.capture_lock.acquire()
                release.set()
                with self.assertRaises(PermissionError):
                    future.result(1)
                self.assertEqual(d.bridge.history, [])
            finally:
                release.set()
                if app.capture_lock.locked():
                    app.capture_lock.release()

    def test_unknown_state_cancels_active_burst(self):
        app = self.app
        app.config["simulation"] = False
        d = app.dispatcher
        d.safety.connected = True
        d.state = {
            "armed": False,
            "motor_activo": False,
            "brazo_ocupado": False,
            "maintenance": False,
        }
        d.state_confirmed_at = time.monotonic()
        app.camera.latest = fixture()
        with patch.object(app.burst, "capture", lambda *a: None):
            app.start_burst("cubo", "rojo", "s", 10, 1)
            d.safety.connected = False
            until(lambda: not app.burst.running)
        self.assertTrue(app.burst.cancel.is_set())

    def test_full_job_queue_does_not_latch_reconfiguration(self):
        app = self.app
        with patch.object(app.jobs, "put_nowait", side_effect=queue.Full):
            with self.assertRaises(RuntimeError):
                app.update_config(defaults())
        self.assertFalse(app.reconfiguring)
        self.assertFalse(app.lifecycle_failed)

    def test_failed_worker_stop_no_duplicate_workers(self):
        app = self.app
        camera = app.camera
        vision = app.vision
        dispatcher = app.dispatcher
        with patch.object(
            app.camera, "stop", side_effect=RuntimeError("Backend atascado")
        ):
            app.update_config(defaults())
            until(lambda: not app.reconfiguring)
        self.assertTrue(app.lifecycle_failed)
        self.assertIs(app.camera, camera)
        self.assertIs(app.vision, vision)
        self.assertIs(app.dispatcher, dispatcher)
        with self.assertRaises(PermissionError):
            app.capture_guard()
        with self.assertRaises(PermissionError):
            app.update_config(defaults())


class DatasetReviewSplitTests(unittest.TestCase):
    def make_dataset(self, root):
        """Manifest de prueba, sin escribir ni contar datos del propietario."""
        from dataset.capture import FIELDS
        import csv

        root = Path(root)
        (root / "metadata").mkdir()
        (root / "images").mkdir()
        rows = []
        for session in range(8):
            for i, shape in enumerate(("cubo", "cilindro", "prisma_triangular")):
                name = f"images/{session}_{shape}.png"
                rng = np.random.default_rng(session * 13 + i)
                cv2.imwrite(
                    str(root / name), rng.integers(0, 255, (24, 32, 3), np.uint8)
                )
                rows.append(
                    {
                        "image": name,
                        "shape": shape,
                        "color": ("rojo", "verde", "azul")[i],
                        "session": f"s{session}",
                        "source": "camara_real",
                    }
                )
        with (root / "metadata/manifest.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            w = csv.DictWriter(stream, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        for row in rows:
            set_review(root, row["image"], "aceptada")
        return rows

    def test_persistent_review_rejection_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            name = rows[0]["image"]
            set_review(d, name, "rechazada")
            self.assertEqual(
                next(r for r in review(d) if r["original"] == name)["review"],
                "rechazada",
            )
            result = split_sessions(d)
            self.assertNotIn(name, [r["original"] for r in result["items"]])
            self.assertEqual(sum(v["total"] for v in result["summary"].values()), 23)
            self.assertTrue(result["training_ready"])
            self.assertEqual(result, split_sessions(d))
            set_review(d, name, "sin_revisar")
            self.assertFalse(
                json.loads((Path(d) / "metadata/split_sessions.json").read_text())[
                    "valid"
                ]
            )

    def test_duplicates_across_sessions_grouped(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            a = rows[0]["image"]
            b = rows[3]["image"]
            (Path(d) / b).write_bytes((Path(d) / a).read_bytes())
            result = split_sessions(d)
            assignments = {r["original"]: r["subset"] for r in result["items"]}
            self.assertEqual(assignments[a], assignments[b])
            self.assertEqual(result["sessions"]["s0"], result["sessions"]["s1"])

    def test_missing_original_or_derived_rejects_split(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            (Path(d) / rows[0]["image"]).unlink()
            with self.assertRaisesRegex(ValueError, "Falta original"):
                split_sessions(d)
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            r = dict(
                rows[0],
                original=rows[0]["image"],
                crop="derived/missing.png",
                review="aceptada",
            )
            (Path(d) / "metadata/vision_v2.jsonl").write_text(json.dumps(r) + "\n")
            with self.assertRaisesRegex(ValueError, "Falta archivo derivado"):
                split_sessions(d)

    def test_unreviewed_split_not_training_ready(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            set_review(d, rows[0]["image"], "sin_revisar")
            result = split_sessions(d)
            self.assertFalse(result["training_ready"])
            self.assertFalse(
                next(r for r in result["items"] if r["original"] == rows[0]["image"])[
                    "eligible_for_training"
                ]
            )

    def test_identical_sessions_cannot_be_split_with_leakage(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            for index, row in enumerate(rows):
                (Path(d) / row["image"]).write_bytes(
                    (Path(d) / rows[index % 3]["image"]).read_bytes()
                )
            with self.assertRaisesRegex(ValueError, "grupos independientes"):
                split_sessions(d)

    def test_invalid_review_and_rejected_file_never_enters_plan(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.make_dataset(d)
            name = rows[0]["image"]
            with self.assertRaises(ValueError):
                set_review(d, name, "aprobada_automaticamente")
            set_review(d, name, "rechazada")
            (Path(d) / name).unlink()
            result = split_sessions(d)
            self.assertNotIn(name, [r["original"] for r in result["items"]])


class OriginalIndependenceUITests(unittest.TestCase):
    def test_original_survives_perception_failure_and_expires(self):
        gc.collect()
        with tempfile.TemporaryDirectory() as d:
            c = defaults()
            c["dataset_dir"] = d
            c["vision"]["rotation"] = 90
            with patch("app.application.load", return_value=c), patch.object(
                HTTPBridge, "request", side_effect=AssertionError("Hardware prohibido")
            ):
                app = Application(True)
                w = MainWindow(app)
                try:
                    with patch.object(
                        app.vision.processor,
                        "process",
                        side_effect=RuntimeError("Fallo inyectado"),
                    ):
                        app.camera.latest = fixture()
                        pump(w, 0.2)
                        self.assertGreater(app.vision.errors, 0)
                        w.auto.update_video(app.camera.snapshot())
                        self.assertIsNotNone(w.auto.video.photo)
                        self.assertIn("Sin observación vigente", w.auto.context.get())
                        self.assertLess(
                            w.auto.video.photo.width(), w.auto.video.photo.height()
                        )
                        w.navigate(2)
                        pump(w, 0.04)
                        w.dataset.update_video(app.camera.snapshot())
                        self.assertIsNotNone(w.dataset.video.photo)
                        for mode in ("Procesada", "Máscara"):
                            w.auto.view.set(mode)
                            w.auto.select_view()
                            w.auto.update_video(app.camera.snapshot())
                            self.assertIsNone(w.auto.video.photo)
                        app.camera.latest = Frame(
                            2,
                            time.monotonic() - 2,
                            scene(),
                            0,
                            "review_fixture",
                            "fixture_prueba",
                        )
                        w.auto.view.set("Original")
                        w.auto.update_video(app.camera.snapshot())
                        w.dataset.update_video(app.camera.snapshot())
                        self.assertIsNone(w.auto.video.photo)
                        self.assertIsNone(w.dataset.video.photo)
                finally:
                    app.close()
                    w.destroy()
                    gc.collect()
