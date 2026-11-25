"""Regresión 03.4-R: fixtures sintéticas y destinos temporales, sin hardware."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from app.config import defaults, validate, save, load
from app.models import Frame, Command
from ai.calibration import sample_region, append_sample, display_rect, overlaps
from ai.perception import Perception
from ai.profiles import Profiles, expanded
from dataset.capture import DatasetCapture
from dataset.normalize import derive, records
from dataset.tools import split_sessions, set_review
from ui.dataset_view import dataset_summary
from tests.test_dispatcher import until


def image(hue=5, s=200, v=180):
    hsv = np.zeros((180, 240, 3), np.uint8)
    hsv[40:120, 60:160] = [hue, s, v]
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def frame(data=None, i=1, source="fixture_prueba", age=0):
    return Frame(
        i,
        time.monotonic() - age,
        image() if data is None else data,
        12,
        "synthetic",
        source,
    )


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.v = defaults()["vision"]

    def test_circular_red_sample(self):
        hsv = np.full((40, 40, 3), (179, 180, 160), np.uint8)
        hsv[:20, :, 0] = 1
        s = sample_region(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), [0, 0, 1, 1])
        self.assertEqual(len(s["ranges"]), 2)
        self.assertLess(s["hue_dispersion"], 3)

    def test_reflections_low_saturation_excluded(self):
        data = image()
        data[:40] = 255
        s = sample_region(data, [0, 0, 1, 1])
        self.assertLess(s["pixels_used"], s["pixels_total"])
        self.assertGreater(s["pixels_used"], 1000)

    def test_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            sample_region(np.zeros((20, 20, 3), np.uint8), [0, 0, 1, 1])

    def test_display_coordinates_no_letterbox(self):
        self.assertEqual(
            display_rect((25, 20), (75, 60), (400, 400, 3), (100, 80)),
            [0.25, 0.25, 0.5, 0.5],
        )

    def test_display_clips_and_reverse(self):
        self.assertEqual(
            display_rect((200, 90), (-5, -9), (100, 100, 3), (100, 80)),
            [0.0, 0.0, 1.0, 1.0],
        )

    def test_tiny_drag_rejected(self):
        with self.assertRaises(ValueError):
            display_rect((1, 1), (2, 2), (100, 100, 3), (100, 100))

    def test_sample_proposal_does_not_mutate_active(self):
        s = sample_region(image(), [0.25, 0.25, 0.4, 0.4])
        new = append_sample(self.v, "rojo", s, "tono")
        self.assertGreater(len(new["hsv"]["rojo"]), len(self.v["hsv"]["rojo"]))
        self.assertEqual(len(self.v["hsv"]["rojo"]), 2)

    def test_same_color_or_one_region(self):
        self.v["hsv"]["rojo"].append([0, 30, 20, 20, 255, 255])
        self.v["interval_meta"]["rojo"].append({"name": "claro", "enabled": True})
        self.assertEqual(
            len(Perception(self.v).process(frame()).observation.objects), 1
        )

    def test_disabled_interval(self):
        for m in self.v["interval_meta"]["rojo"]:
            m["enabled"] = False
        self.assertEqual(
            len(Perception(self.v).process(frame()).observation.objects), 0
        )

    def test_overlap_uncertain(self):
        self.v["hsv"]["verde"] = [[0, 30, 20, 20, 255, 255]]
        self.assertTrue(overlaps(self.v))
        r = Perception(self.v).process(frame())
        self.assertEqual(len(r.observation.objects), 0)
        self.assertEqual(r.rejected[0].color, "incierto")

    def test_expanded_dark_green_blue_red(self):
        for hue in (2, 172, 36, 88, 91, 134):
            with self.subTest(hue=hue):
                self.assertTrue(
                    Perception(expanded(self.v))
                    .process(frame(image(hue, 90, 70)))
                    .observation.objects
                )

    def test_search_roi_excludes_only_outside(self):
        self.v["search_roi"] = {"enabled": True, "rect": [0.0, 0.0, 0.2, 1.0]}
        self.assertFalse(Perception(self.v).process(frame()).observation.objects)
        self.assertEqual(self.v["grip_roi"], defaults()["vision"]["grip_roi"])

    def test_filter_dimension_reject(self):
        self.v["filters"]["min_width"] = 150
        r = Perception(self.v).process(frame())
        self.assertFalse(r.observation.objects)
        self.assertIn("Dimensiones", r.rejected[0].reason)

    def test_filter_relative_area_reject(self):
        self.v["filters"]["min_area_ratio"] = 0.5
        self.assertTrue(Perception(self.v).process(frame()).rejected)

    def test_filter_border_reject(self):
        self.v["filters"]["reject_border"] = True
        self.v["search_roi"] = {"enabled": True, "rect": [0.25, 0.0, 0.5, 1.0]}
        self.assertTrue(Perception(self.v).process(frame()).rejected)

    def test_three_frame_confirmation_and_id(self):
        p = Perception(expanded(self.v))
        ids = []
        for i in range(1, 4):
            r = p.process(frame(i=i))
            ids.append(r.observation.objects[0].track_id)
            self.assertEqual(r.observation.target is not None, i == 3)
        self.assertEqual(len(set(ids)), 1)
        self.assertIsNone(r.observation.predicted_class)

    def test_frozen_frame_cannot_confirm(self):
        p = Perception(expanded(self.v))
        f = frame()
        for _ in range(5):
            self.assertIsNone(p.process(f).observation.target)

    def test_stale_frame_invalidates_target(self):
        p = Perception(self.v)
        self.assertIsNotNone(p.process(frame()).observation.target)
        self.assertIsNone(p.process(frame(age=2)).observation.target)

    def test_generation_resets_confirmation(self):
        p = Perception(expanded(self.v))
        for i in range(3):
            p.process(frame(i=i))
        f = frame(i=10)
        from dataclasses import replace

        self.assertIsNone(p.process(replace(f, generation="other")).observation.target)

    def test_loss_bounded(self):
        p = Perception(self.v)
        p.process(frame())
        blank = np.zeros((180, 240, 3), np.uint8)
        for i in range(20):
            r = p.process(frame(blank, i + 2))
        self.assertEqual(r.observation.tracking_state, "Sin objetivo")
        self.assertFalse(p.tracker.tracks)

    def test_validation_invalid_roi(self):
        self.v["search_roi"]["rect"] = [0.9, 0, 0.5, 1]
        with self.assertRaises(ValueError):
            validate(dict(defaults(), vision=self.v))

    def test_migrate_schema2_preserves_rotation_and_hsv(self):
        c = defaults()
        c["schema_version"] = 2
        for key in (
            "interval_meta",
            "search_roi",
            "filters",
            "tracking",
            "profile_name",
        ):
            del c["vision"][key]
        for key in ("search", "discarded", "regions"):
            del c["vision"]["overlays"][key]
        c["vision"]["rotation"] = 90
        new = validate(c)
        self.assertEqual(new["schema_version"], 3)
        self.assertEqual(new["vision"]["rotation"], 90)
        self.assertEqual(new["vision"]["hsv"], self.v["hsv"])

    def test_profiles_protected_roundtrip_and_orientation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Profiles(self.v, Path(d) / "catalog.json")
            p.save()
            v = p.select("Ampliado experimental", dict(self.v, rotation=270))
            self.assertEqual(v["rotation"], 270)
            self.assertEqual(v["tracking"]["confirm_frames"], 3)
            for fn in (
                lambda: p.delete("Original"),
                lambda: p.put("Original", v),
                lambda: p.rename("Original", "x"),
            ):
                with self.assertRaises(ValueError):
                    fn()
            p.put("Borrador", v)
            p.rename("Borrador", "Campo")
            q = Profiles(self.v, p.path)
            self.assertIn("Campo", q.data)
            q.delete("Campo")
            self.assertNotIn("Campo", q.data)


class DatasetCalibrationTests(unittest.TestCase):
    def test_negative_separate_count_and_context(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            _, r = c.save_record(
                frame(source="camara_real"),
                "no_objetivo",
                "sin_color",
                "negativos",
                defaults(),
                metadata={"lighting": "sombra"},
            )
            summary = dataset_summary(d)
            self.assertEqual(summary["total"], 0)
            self.assertEqual(summary["negatives"], 1)
            self.assertEqual(c.counts(), dict(cubo=0, cilindro=0, prisma_triangular=0))
            self.assertEqual(r["capture_context"]["lighting"], "sombra")

    def test_no_target_color_positive_rejected(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            DatasetCapture(d).save_record(frame(), "cubo", "sin_color", "s", defaults())

    def test_derive_preserves_original_and_trace(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            path, r = c.save_record(
                frame(source="camara_real"), "cubo", "rojo", "s", defaults()
            )
            before = {p: p.read_bytes() for p in Path(d).rglob("*") if p.is_file()}
            item = derive(d, r["original"], defaults(), 270)
            self.assertEqual(item["orientation_origin"], "confirmacion_operador")
            self.assertEqual(item["rotation"], 270)
            self.assertEqual(
                cv2.imread(str(Path(d) / item["normalized"])).shape[:2], (240, 180)
            )
            self.assertEqual(
                records(d)[0]["original_sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            for p, b in before.items():
                self.assertEqual(p.read_bytes(), b)

    def test_derive_uses_per_image_orientation(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            _, r = c.save_record(
                frame(source="camara_real"), "cubo", "rojo", "s", defaults()
            )
            config = defaults()
            config["vision"]["rotation"] = 270
            item = derive(d, r["original"], config)
            self.assertEqual(item["rotation"], 0)
            self.assertEqual(item["orientation_origin"], "metadata")

    def test_unknown_old_orientation_requires_choice(self):
        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            path = c.save(frame(source="camara_real"), "cubo", "rojo", "s")
            name = path.relative_to(d).as_posix()
            with self.assertRaises(ValueError):
                derive(d, name, defaults())
            self.assertEqual(derive(d, name, defaults(), 90)["rotation"], 90)

    def test_context_validation(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            DatasetCapture(d).save_record(
                frame(), "cubo", "rojo", "s", defaults(), metadata={"unknown": "secret"}
            )


class AcceptedTargetsTests(unittest.TestCase):
    def test_cache_ack_stop_release_and_rejection(self):
        from control.command_dispatcher import Dispatcher
        from control.controller import Controller
        from hardware.simulator import Simulator

        sim = Simulator()
        d = Dispatcher(sim, sim, defaults())
        controller = Controller(d)
        controller.change_mode("manual")
        d.start()

        def send(action, p=None):
            if action in ("servo", "release"):
                until_idle = time.monotonic() + 1.5
                while sim.busy() and time.monotonic() < until_idle:
                    controller.tick()
                    sim.request("state")
                    time.sleep(0.02)
            controller.tick()
            return d.submit(Command(action, p or {})).result(2)

        try:
            send("verify")
            send("arm")
            send("enable", {"nombre": "base"})
            self.assertNotIn("base", d.accepted_servo_targets)
            send("servo", {"nombre": "base", "grado": 80})
            self.assertEqual(d.accepted_servo_targets["base"]["degree"], 80)
            d.stop()
            send("release", {"nombre": "base", "confirm": 1})
            self.assertFalse(d.accepted_servo_targets)
            send("verify")
            send("arm")
            send("enable", {"nombre": "base"})
            send("servo", {"nombre": "base", "grado": 70})
            d.stop()
            self.assertFalse(d.accepted_servo_targets)
        finally:
            d.close()


class CalibrationIntegrationTests(unittest.TestCase):
    def setUp(self):
        import gc

        gc.collect()
        self.temp = tempfile.TemporaryDirectory()
        self.c = defaults()
        self.c["dataset_dir"] = self.temp.name
        from hardware.camera import Camera
        from hardware.bridge import HTTPBridge

        self.patches = [
            patch("app.application.load", return_value=self.c),
            patch.object(
                Camera, "_open", side_effect=AssertionError("Hardware prohibido")
            ),
            patch.object(
                HTTPBridge, "request", side_effect=AssertionError("Hardware prohibido")
            ),
        ]
        for p in self.patches:
            p.start()
        from app.application import Application
        from ui.main_window import MainWindow

        self.app = Application(True)
        self.window = MainWindow(self.app)
        from tests.test_ui_redesign import pump

        pump(self.window, 0.15)

    def tearDown(self):
        self.app.close()
        self.window.destroy()
        for p in self.patches:
            p.stop()
        self.temp.cleanup()

    def test_calibrator_reuses_camera_and_discards_draft(self):
        from ui.color_calibrator import Calibrator
        from tests.test_ui_redesign import pump

        camera = self.app.camera
        dialog = Calibrator(self.window, self.app)
        pump(self.window, 0.12)
        self.assertIs(dialog.worker.camera, camera)
        self.assertEqual(len(self.app.calibration_workers), 1)
        dialog.draft["hsv"]["rojo"][0][1] = 20
        dialog.preview()
        dialog.close()
        self.assertEqual(self.app.config["vision"]["hsv"]["rojo"][0][1], 90)
        self.assertFalse(self.app.calibration_workers)
        self.assertFalse(dialog.worker.thread.is_alive())
        self.assertFalse(self.app.dispatcher.bridge.history)

    def test_apply_visual_preserves_workers_and_control(self):
        camera = self.app.camera
        vision = self.app.vision
        dispatcher = self.app.dispatcher
        profile = expanded(self.c["vision"])
        with patch("app.application.save") as saving:
            self.app.update_vision(profile)
            until(
                lambda: self.app.config["vision"]["profile_name"]
                == "Ampliado experimental"
            )
            self.assertEqual(saving.call_count, 1)
        self.assertIs(camera, self.app.camera)
        self.assertIs(vision, self.app.vision)
        self.assertIs(dispatcher, self.app.dispatcher)
        self.assertFalse(dispatcher.bridge.history)
        dispatcher.state["maintenance"] = True
        with self.assertRaises(PermissionError):
            self.app.vision_guard()
        dispatcher.state["maintenance"] = False

    def test_manual_draft_steps_do_not_send_and_stop_invalidates(self):
        m = self.window.manual
        m.sync_targets()
        with self.assertRaises(ValueError):
            m.fine("base", 1)
        m.angles["base"].set("75")
        m.fine("base", 5)
        m.fine("base", -1)
        self.assertEqual(m.angles["base"].get(), "79")
        self.assertFalse(self.app.dispatcher.bridge.history)
        self.app.dispatcher.stop()
        m.sync_targets()
        self.assertFalse(m.draft_valid["base"])

    def test_base_dialog_initial_slider_does_not_create_reference(self):
        m = self.window.manual
        m.sync_targets()
        m.base_dialog()
        self.assertFalse(m.draft_valid["base"])
        self.assertFalse(self.app.dispatcher.bridge.history)


class DerivativeReviewTests(unittest.TestCase):
    def test_derivative_review_independent_invalidates_split(self):
        from dataset.normalize import set_derivative_review

        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            _, r = c.save_record(
                frame(source="camara_real"), "cubo", "rojo", "s", defaults()
            )
            item = derive(d, r["original"], defaults(), 90)
            set_review(d, r["original"], "aceptada")
            set_derivative_review(d, item["normalized"], "rechazada")
            self.assertEqual(records(d)[0]["review"], "rechazada")
            self.assertEqual(
                __import__("dataset.tools", fromlist=["review"]).review(d)[0]["review"],
                "aceptada",
            )
            with self.assertRaises(ValueError):
                set_derivative_review(d, "derived/missing.png", "aceptada")

    def test_derivatives_group_with_original_and_missing_rejected(self):
        from dataset.normalize import set_derivative_review

        with tempfile.TemporaryDirectory() as d:
            c = DatasetCapture(d)
            rng = np.random.default_rng(42)
            first = None
            for session in range(4):
                for shape in ("cubo", "cilindro", "prisma_triangular"):
                    data = rng.integers(0, 256, (60, 80, 3), dtype=np.uint8)
                    _, r = c.save_record(
                        frame(data, source="camara_real"),
                        shape,
                        "rojo",
                        f"s{session}",
                        defaults(),
                    )
                    set_review(d, r["original"], "aceptada")
                    if first is None:
                        first = r
            item = derive(d, first["original"], defaults(), 270)
            set_derivative_review(d, item["normalized"], "aceptada")
            plan = split_sessions(d)
            row = next(r for r in plan["items"] if r["original"] == first["original"])
            self.assertEqual(row["normalizations"][0]["normalized"], item["normalized"])
            self.assertTrue(plan["training_ready"])
            (Path(d) / item["normalized"]).unlink()
            with self.assertRaises(ValueError):
                split_sessions(d)


class LateServoAckTests(unittest.TestCase):
    def test_late_ack_after_stop_never_restores_target(self):
        import threading
        from control.command_dispatcher import Dispatcher
        from hardware.simulator import Simulator

        sim = Simulator()
        entered = threading.Event()
        unblock = threading.Event()

        class Delayed:
            def request(self, action, params=None):
                if action == "servo":
                    entered.set()
                    unblock.wait(2)
                    return {"ok": True}
                return sim.request(action, params)

            def close(self):
                pass

        d = Dispatcher(Delayed(), sim, defaults())
        d.safety.mode = "manual"
        d.safety.touch()
        d.start()
        try:
            d.submit(Command("verify")).result(1)
            d.submit(Command("arm")).result(1)
            pending = d.submit(Command("servo", {"nombre": "base", "grado": 80}))
            self.assertTrue(entered.wait(0.5))
            d.stop()
            unblock.set()
            with self.assertRaises(PermissionError):
                pending.result(1)
            self.assertFalse(d.accepted_servo_targets)
        finally:
            unblock.set()
            d.close()


class AdditionalVisionTests(unittest.TestCase):
    def test_same_color_proximity_distinct_tracks(self):
        data = np.zeros((180, 240, 3), np.uint8)
        data[20:60, 20:60] = (0, 0, 200)
        data[100:140, 170:210] = (0, 0, 200)
        p = Perception(expanded(defaults()["vision"]))
        for i in range(3):
            r = p.process(frame(data, i))
        self.assertEqual(len(r.observation.objects), 2)
        self.assertEqual(len({o.track_id for o in r.observation.objects}), 2)
        self.assertTrue(all(o.confirmed for o in r.observation.objects))

    def test_disabled_overlap_is_not_ambiguous(self):
        v = defaults()["vision"]
        v["hsv"]["verde"] = [[0, 30, 20, 20, 255, 255]]
        v["interval_meta"]["verde"][0]["enabled"] = False
        self.assertFalse(overlaps(v))
        self.assertEqual(
            Perception(v).process(frame()).observation.objects[0].color, "rojo"
        )

    def test_filter_aspect_and_extent(self):
        for key, value in (("aspect_max", 1.1), ("extent_min", 1.0)):
            v = defaults()["vision"]
            v["filters"][key] = value
            self.assertTrue(Perception(v).process(frame()).rejected)

    def test_hsv_interval_strict_validation(self):
        for bounds in (
            [180, 0, 0, 190, 255, 255],
            [10, 200, 0, 5, 255, 255],
            [1, 2, 3],
        ):
            c = defaults()
            c["vision"]["hsv"]["verde"] = [bounds]
            with self.assertRaises(ValueError):
                validate(c)

    def test_profile_persist_does_not_change_current(self):
        v = defaults()["vision"]
        old = copy.deepcopy(v)
        with tempfile.TemporaryDirectory() as d:
            Profiles(v, Path(d) / "p.json").put("Prueba", expanded(v))
        self.assertEqual(v, old)


class CalibrationShutdownTests(unittest.TestCase):
    def test_failed_calibrator_stop_still_closes_other_workers(self):
        from app.application import Application
        from unittest.mock import Mock

        with patch("app.application.load", return_value=defaults()):
            app = Application(True)
        worker = Mock()
        worker.stop.side_effect = RuntimeError("fallo de prueba")
        app.calibration_workers.add(worker)
        with self.assertRaises(RuntimeError):
            app.close()
        self.assertFalse(app.dispatcher.worker.is_alive())
        self.assertFalse(app.dispatcher.supervisor.is_alive())
        self.assertFalse(app.vision.thread.is_alive())
        self.assertTrue(app.closed)
