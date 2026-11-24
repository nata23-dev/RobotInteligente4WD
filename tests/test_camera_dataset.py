import csv
from pathlib import Path
import tempfile
import threading
import time
import unittest
import cv2
import numpy as np
from app.config import defaults
from app.models import Frame
from hardware.camera import Camera
from dataset.capture import DatasetCapture
from tests.test_dispatcher import until


class FakeCapture:
    def __init__(self): self.released = False
    def isOpened(self): return True
    def read(self):
        time.sleep(.01)
        return True, np.zeros((24, 32, 3), np.uint8)
    def release(self): self.released = True


class CameraTests(unittest.TestCase):
    def test_latest_frame_bounded_and_close(self):
        c = defaults()
        c['camera_url'] = 'http://fixture/stream'
        capture = FakeCapture()
        camera = Camera(c, factory=lambda url: capture)
        camera.start()
        try:
            until(lambda: camera.snapshot()['frame'] is not None)
            first = camera.snapshot()['frame'].id
            time.sleep(.08)
            snap = camera.snapshot()
            self.assertGreater(snap['frame'].id, first)
            self.assertTrue(snap['fresh'])
            self.assertEqual(snap['frame'].image.shape, (24, 32, 3))
            with self.assertRaises(RuntimeError): camera.start()
        finally:
            camera.stop()
        self.assertTrue(capture.released)
        self.assertFalse(camera.thread.is_alive())
        self.assertIsNone(camera.snapshot()['frame'])

    def test_stale_frame(self):
        camera = Camera(defaults())
        camera.latest = Frame(1, time.monotonic() - 2, np.zeros((2, 2, 3), np.uint8))
        self.assertFalse(camera.snapshot()['fresh'])
        self.assertEqual(camera.snapshot()['status'], 'Video atrasado')

    def test_loss_reconnect_and_release(self):
        config = defaults()
        config.update(camera_url='http://fixture/stream', camera_retry_s=.2)
        captures = []
        class Broken(FakeCapture):
            def read(self): return False, None
        def factory(url):
            c = Broken()
            captures.append(c)
            return c
        camera = Camera(config, factory=factory)
        camera.start()
        until(lambda: camera.errors >= 2)
        camera.stop()
        self.assertTrue(all(c.released for c in captures))
        self.assertIsNone(camera.snapshot()['frame'])

    def test_no_url(self):
        with self.assertRaises(ValueError): Camera(defaults()).start()


class DatasetTests(unittest.TestCase):
    def frame(self):
        # Fixture sintético exclusivo de pruebas; nunca se incorpora al dataset real.
        return Frame(10, time.monotonic(), np.full((20, 30, 3), (20, 80, 200), np.uint8))

    def test_original_png_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = DatasetCapture(directory)
            f = self.frame()
            path = capture.save(f, 'cubo', 'rojo', 'sesion_01', source='fixture_prueba')
            np.testing.assert_array_equal(cv2.imread(str(path)), f.image)
            with (Path(directory) / 'metadata' / 'manifest.csv').open(encoding='utf-8', newline='') as stream:
                row = list(csv.DictReader(stream))[0]
            self.assertEqual(row['shape'], 'cubo')
            self.assertEqual(row['frame_id'], '10')
            self.assertEqual(row['source'], 'fixture_prueba')
            self.assertEqual(capture.counts()['cubo'], 0)

    def test_reject_stale_and_bad_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            c = DatasetCapture(directory)
            old = Frame(1, time.monotonic() - 5, self.frame().image)
            with self.assertRaises(ValueError): c.save(old, 'cubo', 'rojo', 's')
            for shape, color, session in [('esfera', 'rojo', 's'), ('cubo', 'rosa', 's'), ('cubo', 'rojo', '../escape')]:
                with self.assertRaises(ValueError): c.save(self.frame(), shape, color, session)
            self.assertEqual(list(Path(directory).rglob('*.png')), [])

    def test_no_filename_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            c = DatasetCapture(directory)
            f = self.frame()
            a = c.save(f, 'cilindro', 'verde', 's', source='fixture_prueba')
            b = c.save(f, 'cilindro', 'verde', 's', source='fixture_prueba')
            self.assertNotEqual(a, b)

    def test_aruco_distribution_available(self):
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        detector = cv2.aruco.ArucoDetector(dictionary)
        for marker_id in (0, 1, 2):
            marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 160)
            image = cv2.copyMakeBorder(marker, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
            _, ids, _ = detector.detectMarkers(image)
            self.assertEqual(ids.flatten().tolist(), [marker_id])
