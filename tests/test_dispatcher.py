from concurrent.futures import CancelledError
import threading
import time
import unittest
from app.config import defaults
from app.models import Command
from control.command_dispatcher import Dispatcher
from control.controller import Controller
from hardware.protocol import APIError
from hardware.simulator import Simulator


def until(predicate, timeout=2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(.01)
    raise AssertionError('No se cumplió la condición dentro del plazo')


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulator()
        self.d = Dispatcher(self.sim, self.sim, defaults())
        self.ctrl = Controller(self.d)
        self.ctrl.change_mode('manual')
        self.d.start()
        self.ctrl.tick()

    def tearDown(self):
        self.d.close()

    def send(self, a, p=None):
        self.ctrl.tick()
        return self.d.submit(Command(a, p or {})).result(2)

    def arm(self):
        self.send('verify')
        self.send('arm')

    def test_initial_no_commands_and_unauthorized(self):
        time.sleep(.05)
        self.assertEqual(self.sim.history, [])
        with self.assertRaises(PermissionError):
            self.send('drive', {'fl': 1, 'fr': 1, 'rl': 1, 'rr': 1, 'ms': 150})

    def test_verify_does_not_arm(self):
        self.send('verify')
        self.assertFalse(self.d.safety.session)
        self.assertFalse(self.sim.armed)

    def test_explicit_arm_and_serial_heartbeat(self):
        self.arm()
        deadline = time.monotonic() + .8
        while time.monotonic() < deadline:
            self.ctrl.tick()
            time.sleep(.03)
        self.assertTrue(self.sim.request('state')['armed'])
        seqs = [p['seq'] for a, p in self.sim.history if a == 'heartbeat']
        self.assertGreaterEqual(len(seqs), 2)
        self.assertEqual(seqs, sorted(set(seqs)))

    def test_controller_failure_does_not_renew_forever(self):
        self.arm()
        until(lambda: not self.d.safety.session, timeout=1.5)
        # "no confirmada" también contiene "confirmada": esperar el estado
        # positivo exacto antes de comprobar el STOP remoto evita una carrera.
        until(lambda: self.d.safety.status == 'Parada confirmada (estado lógico)')
        self.assertFalse(self.sim.request('state')['armed'])

    def test_stop_cancels_pending_and_latches(self):
        self.arm()
        with self.d.safety.lock:
            futures = [self.d.submit(Command('drive', {'fl': 1, 'fr': 1, 'rl': 1, 'rr': 1, 'ms': 150})) for _ in range(5)]
            self.d.stop()
            self.assertFalse(self.d.safety.session)
        until(lambda: self.d.stop_thread and not self.d.stop_thread.is_alive())
        self.assertTrue(all(f.cancelled() or f.done() for f in futures))
        with self.assertRaises(PermissionError):
            self.send('drive', {'fl': 1, 'fr': 1, 'rl': 1, 'rr': 1, 'ms': 150})

    def test_loss_invalidates_and_stop_unconfirmed(self):
        self.arm()
        self.sim.online = False
        until(lambda: not self.d.safety.session)
        until(lambda: 'no confirmada' in self.d.safety.status)
        self.assertFalse(self.d.safety.connected)

    def test_modes_are_exclusive(self):
        self.arm()
        self.ctrl.change_mode('dataset')
        self.assertFalse(self.d.safety.session)
        with self.assertRaises(PermissionError): self.send('arm')
        with self.assertRaises(NotImplementedError): self.ctrl.start_autonomous()

    def test_firmware_busy_no_retries(self):
        self.arm()
        self.send('enable', {'nombre': 'base'})
        with self.assertRaises(APIError):
            self.send('drive', {'fl': 1, 'fr': 1, 'rl': 1, 'rr': 1, 'ms': 150})
        self.assertEqual(len([a for a, p in self.sim.history if a == 'drive']), 1)

    def test_release_confirmation_enforced_locally(self):
        self.send('verify')
        with self.assertRaises(PermissionError): self.send('release', {'nombre': 'base', 'confirm': 0})

    def test_workers_close(self):
        self.arm()
        self.d.close()
        self.assertFalse(self.d.worker.is_alive())
        self.assertFalse(self.d.supervisor.is_alive())
        self.assertFalse(self.sim.armed)


class StopRaceTests(unittest.TestCase):
    def test_stop_during_arm_response(self):
        sim = Simulator()
        entered, unblock = threading.Event(), threading.Event()
        class Delayed:
            def request(self, action, params=None):
                result = sim.request(action, params)
                if action == 'arm':
                    entered.set()
                    unblock.wait(2)
                return result
            def close(self): pass
        d = Dispatcher(Delayed(), sim, defaults())
        d.safety.mode = 'manual'
        d.safety.touch()
        d.start()
        try:
            d.submit(Command('verify')).result(2)
            future = d.submit(Command('arm'))
            self.assertTrue(entered.wait(1))
            d.stop()
            until(lambda: not sim.request('state')['armed'])
            unblock.set()
            with self.assertRaises(PermissionError): future.result(2)
            until(lambda: not d.stop_thread.is_alive())
            self.assertFalse(d.safety.session)
            self.assertFalse(sim.request('state')['armed'])
        finally:
            unblock.set()
            d.close()

    def test_stop_bypasses_blocked_transport(self):
        sim = Simulator()
        entered, unblock = threading.Event(), threading.Event()
        class Delayed:
            def request(self, action, params=None):
                if action == 'drive':
                    entered.set()
                    unblock.wait(2)
                return sim.request(action, params)
            def close(self): pass
        d = Dispatcher(Delayed(), sim, defaults())
        d.safety.mode = 'manual'
        d.safety.touch()
        d.start()
        try:
            d.submit(Command('verify')).result(1)
            d.submit(Command('arm')).result(1)
            future = d.submit(Command('drive', {'fl': 1, 'fr': 1, 'rl': 1, 'rr': 1, 'ms': 150}))
            self.assertTrue(entered.wait(1))
            d.stop()
            until(lambda: not sim.request('state')['armed'], timeout=.5)
            self.assertFalse(d.safety.session)
            unblock.set()
            with self.assertRaises(APIError): future.result(2)
            self.assertFalse(sim.request('state')['motor_activo'])
        finally:
            unblock.set()
            d.close()
