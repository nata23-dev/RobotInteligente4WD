import copy
import json
from pathlib import Path
import tempfile
import unittest
from app.config import defaults, validate, save, load, pattern
from hardware.protocol import validate_command


class ConfigTests(unittest.TestCase):
    def test_defaults_and_persistence(self):
        c = defaults()
        c['pulse_ms'] = 200
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'config.local.json'
            save(c, p)
            self.assertEqual(load(p), c)
            self.assertFalse(p.with_suffix('.tmp').exists())

    def test_absent_private_file(self):
        self.assertEqual(load(Path('no-existe.local.json')), defaults())

    def test_invalid_pulses(self):
        for v in (49, 701, True, 150.1):
            c = defaults()
            c['pulse_ms'] = v
            with self.subTest(v=v), self.assertRaises(ValueError):
                validate(c)

    def test_patterns(self):
        for p in ([0, 0, 0, 0], [1, 1], [True, 1, 0, 0], [2, 0, 1, 1]):
            with self.subTest(p=p), self.assertRaises(ValueError):
                pattern(p)
        pattern([-1, 1, -1, 1])
        self.assertEqual(defaults()['patterns']['izquierda'], [1, 1, -1, -1])

    def test_servo_hard_limits_and_home(self):
        for name, field, value in [('garra', 'min', 34), ('garra', 'max', 61),
                                    ('base', 'max', 116), ('base', 'home', 80), ('garra', 'max', 55)]:
            c = defaults()
            c['servos'][name][field] = value
            with self.subTest(name=name, field=field), self.assertRaises(ValueError):
                validate(c)

    def test_network_and_times(self):
        for field, value in [('robot_url', 'http://user:pass@robot'), ('robot_url', 'ftp://robot'),
                              ('timeout_s', 5), ('heartbeat_s', .8), ('api_key', 'corta'),
                              ('controller_lease_s', float('nan')), ('camera_url', 'http://robot:99999/stream')]:
            c = defaults()
            c[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(c)

    def test_unknown_fields_and_missing_patterns(self):
        c = defaults()
        c['extra'] = 1
        with self.assertRaises(ValueError):
            validate(c)
        c = defaults()
        del c['patterns']['izquierda']
        with self.assertRaises(ValueError):
            validate(c)

    def test_public_example_and_ignore(self):
        from app.config import ROOT
        c = json.loads((ROOT / 'config.example.json').read_text(encoding='utf-8'))
        self.assertEqual(c['api_key'], '')
        self.assertTrue(c['simulation'])
        ignore = (ROOT / '.gitignore').read_text()
        for value in ('config.local.json', 'referencias_locales/', '.venv/', '*.zip', 'Robot4WD_Firmware_V1.ino'):
            self.assertIn(value, ignore)

    def test_protocol_rejects_incorrect_fields(self):
        with self.assertRaises(ValueError):
            validate_command('drive', {'ms': 100})
        with self.assertRaises(ValueError):
            validate_command('release', {'nombre': 'base', 'confirm': 0})
        with self.assertRaises(ValueError):
            validate_command('heartbeat', {'session': 1, 'seq': 0})
