import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from app.application import Application
from app.config import defaults
from app.models import Command
from tests.test_dispatcher import until


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.load_patch = patch('app.application.load', return_value=defaults())
        self.load_patch.start()
        self.app = Application(simulation=True)
        self.app.controller.change_mode('manual')
        self.app.controller.tick()

    def tearDown(self):
        self.app.close()
        self.load_patch.stop()

    def test_start_no_network_or_arm(self):
        self.assertEqual(self.app.dispatcher.bridge.history, [])
        self.assertFalse(self.app.dispatcher.safety.session)

    def test_change_config_rebuilds_disarmed(self):
        c = defaults()
        c['pulse_ms'] = 200
        with patch('app.application.save') as saving:
            self.app.update_config(c)
            until(lambda: not self.app.reconfiguring)
            saving.assert_called_once_with(c)
        self.assertEqual(self.app.config['pulse_ms'], 200)
        self.assertFalse(self.app.dispatcher.safety.session)
        self.assertFalse(self.app.dispatcher.safety.connected)

    def test_change_config_rejected_when_armed(self):
        d = self.app.dispatcher
        d.submit(Command('verify')).result(1)
        d.submit(Command('arm')).result(1)
        with self.assertRaises(PermissionError): self.app.update_config(defaults())

    def test_close_all_workers(self):
        self.app.close()
        self.assertFalse(self.app.worker.is_alive())
        self.assertFalse(self.app.dispatcher.worker.is_alive())
