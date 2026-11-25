import threading
import time
import unittest
import cv2
import numpy as np
from app.config import defaults
from app.models import Frame
from ai.perception import Perception, Tracker
from ai.vision import VisionWorker
from hardware.camera import Camera
from tests.vision_fixtures import scene
from tests.test_dispatcher import until


def frame(image=None, identity=1, generation="fixture_session"):
    return Frame(
        identity,
        time.monotonic(),
        scene() if image is None else image,
        12,
        generation,
        "fixture_prueba",
    )


class PerceptionTests(unittest.TestCase):
    def setUp(self):
        self.p = Perception(defaults()["vision"])

    def test_colors_boxes_centroids_and_error(self):
        f = frame()
        r = self.p.process(f)
        o = r.observation
        self.assertEqual(o.frame_id, f.id)
        self.assertEqual(o.generation, f.generation)
        self.assertEqual({x.color for x in o.objects}, {"rojo", "verde", "azul"})
        red = next(x for x in o.objects if x.color == "rojo")
        self.assertAlmostEqual(red.centroid[0], (640 // 9 + 640 // 3) / 2, delta=1)
        self.assertLess(red.error_x, 0)
        self.assertGreater(red.area_ratio, 0)
        self.assertEqual(red.box[:2], (640 // 9, 480 // 3))
        self.assertIsNone(o.shape)
        self.assertIsNone(o.confidence)
        np.testing.assert_array_equal(f.image, r.normalized)
        self.assertFalse(np.array_equal(r.overlay, f.image))

    def test_both_red_intervals(self):
        hsv = np.zeros((100, 200, 3), np.uint8)
        hsv[:, :100] = (3, 220, 210)
        hsv[:, 100:] = (175, 220, 210)
        r = self.p.process(frame(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)))
        self.assertTrue(np.all(r.masks["rojo"] == 255))

    def test_empty_and_noise(self):
        a = np.zeros((240, 320, 3), np.uint8)
        a[::9, ::9] = (0, 0, 255)
        self.assertEqual(self.p.process(frame(a)).observation.objects, ())
        self.assertEqual(
            self.p.process(frame(np.full_like(a, 200))).observation.markers, ()
        )

    def test_multiple_objects_and_tracking_continuity_loss(self):
        r = self.p.process(frame())
        target = r.observation.target
        self.assertIsNotNone(target)
        self.assertEqual(
            self.p.process(frame(identity=2)).observation.tracking_state,
            "Objetivo seguido",
        )
        empty = np.full((480, 640, 3), 200, np.uint8)
        r = self.p.process(frame(empty, 3))
        self.assertIsNone(r.observation.target)
        self.assertEqual(r.observation.tracking_state, "Objetivo perdido")
        for n in range(5):
            r = self.p.process(frame(empty, 4 + n))
        self.assertEqual(r.observation.tracking_state, "Sin objetivo")

    def test_generation_resets_tracker(self):
        self.p.process(frame())
        self.assertEqual(
            self.p.process(frame(generation="new")).observation.tracking_state,
            "Objetivo detectado",
        )

    def test_markers_all_and_unknown_rotated(self):
        self.assertEqual(
            {m.id for m in self.p.process(frame()).observation.markers}, {0, 1, 2}
        )
        d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        for identity in (0, 1, 2, 17):
            for rotation in range(4):
                marker = np.rot90(
                    cv2.aruco.generateImageMarker(d, identity, 160), rotation
                )
                image = cv2.cvtColor(
                    cv2.copyMakeBorder(
                        marker, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255
                    ),
                    cv2.COLOR_GRAY2BGR,
                )
                markers = self.p.process(frame(image)).observation.markers
                self.assertEqual(len(markers), 1)
                self.assertEqual(markers[0].id, identity)
                self.assertEqual(markers[0].station is None, identity == 17)

    def test_orientation_coordinates_and_roi(self):
        c = defaults()["vision"]
        c["rotation"] = 90
        r = Perception(c).process(frame())
        self.assertEqual(r.observation.dimensions, (480, 640))
        red = next(x for x in r.observation.objects if x.color == "rojo")
        self.assertAlmostEqual(red.centroid[0], 239, delta=2)

    def test_worker_latest_freshness_and_close(self):
        c = defaults()
        camera = Camera(c)
        worker = VisionWorker(camera, c)
        camera.latest = frame()
        worker.start()
        try:
            until(lambda: worker.snapshot()["result"] is not None)
            first = len(worker.times)
            time.sleep(0.04)
            self.assertEqual(len(worker.times), first)
            for i in range(2, 9):
                camera.latest = frame(identity=i)
            until(lambda: worker.snapshot()["result"].frame.id == 8)
            camera.latest = None
            self.assertIsNone(worker.snapshot()["result"])
            camera.latest = Frame(
                9, time.monotonic() - 5, scene(), 0, "fixture_session", "fixture_prueba"
            )
            self.assertIsNone(worker.snapshot()["result"])
        finally:
            worker.stop()
        self.assertFalse(worker.thread.is_alive())

    def test_slow_processing_discarded_after_reconnect(self):
        c = defaults()
        camera = Camera(c)
        ready = threading.Event()
        release = threading.Event()
        p = self.p

        class Slow:
            def process(self, f):
                ready.set()
                release.wait(1)
                return p.process(f)

        camera.latest = frame()
        worker = VisionWorker(camera, c, Slow())
        worker.start()
        try:
            self.assertTrue(ready.wait(1))
            camera.latest = frame(identity=2, generation="new")
            release.set()
            until(lambda: worker.snapshot()["result"] is not None)
            self.assertEqual(worker.snapshot()["result"].frame.generation, "new")
        finally:
            release.set()
            worker.stop()
