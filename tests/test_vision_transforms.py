import copy
import json
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from app.config import defaults, load, save, validate
from ai.transforms import normalize, digital, fit_size


class TransformTests(unittest.TestCase):
    def test_rotations_and_original_preserved(self):
        a = np.arange(18, dtype=np.uint8).reshape(2,3,3)
        before = a.copy()
        for angle, k in ((0,0),(90,-1),(180,2),(270,1)):
            c = defaults()['vision']; c['rotation'] = angle
            np.testing.assert_array_equal(normalize(a,c), np.rot90(a,k))
        np.testing.assert_array_equal(a,before)

    def test_flips(self):
        a = np.arange(18, dtype=np.uint8).reshape(2,3,3)
        c = defaults()['vision']; c['flip_horizontal'] = True
        np.testing.assert_array_equal(normalize(a,c), a[:,::-1])
        c['flip_vertical'] = True
        np.testing.assert_array_equal(normalize(a,c), a[::-1,::-1])

    def test_neutral_and_digital_non_destructive(self):
        a = np.full((30,40,3),120,np.uint8)
        c = defaults()['vision']['digital']
        np.testing.assert_array_equal(digital(a,c),a)
        c['brightness'] = 10
        self.assertEqual(int(digital(a,c)[0,0,0]),130)
        self.assertEqual(int(a[0,0,0]),120)

    def test_up_down_and_dimensions(self):
        self.assertEqual(fit_size(320,240,(800,600)),(800,600))
        self.assertEqual(fit_size(1920,1080,(640,480)),(640,360))
        self.assertEqual(fit_size(240,320,(800,600)),(450,600))

    def test_migrate_preserves_private_values(self):
        old = defaults()
        for k in ('vision','dataset_options','schema_version'): old.pop(k)
        old.update(timeout_s=.18, heartbeat_s=.25, robot_url='http://fixture.local', api_key='fixture-no-real-value')
        original = copy.deepcopy(old)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.local.json'; p.write_text(json.dumps(old))
            migrated=load(p)
            self.assertEqual({k:migrated[k] for k in old},original)
            self.assertEqual(json.loads(p.read_text()),old)
            save(migrated,p); self.assertEqual(load(p),migrated)

    def test_strict_config(self):
        for path,value in [('rotation',45),('grip_roi',[.9,0,.3,.3]),('open_kernel',2),('digital',{'brightness':0})]:
            c=defaults();c['vision'][path]=value
            with self.assertRaises(ValueError):validate(c)
        c=defaults(); c['vision']['hsv']['rojo'][1]=[179,0,0,170,255,255]
        with self.assertRaises(ValueError):validate(c)
