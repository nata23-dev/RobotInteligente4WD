import unittest
from hardware.simulator import Simulator
from hardware.protocol import APIError


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now
    def advance(self, value): self.now += value


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.sim = Simulator(clock=self.clock)
        self.session = 0
        self.seq = 0

    def arm(self):
        self.session = self.sim.request('arm', {'challenge': self.sim.request('state')['challenge']})['session']

    def send(self, action, **params):
        self.seq += 1
        return self.sim.request(action, params | {'session': self.session, 'seq': self.seq})

    def drive(self):
        return self.send('drive', fl=-1, fr=1, rl=-1, rr=1, ms=150)

    def test_boot(self):
        self.assertFalse(self.sim.request('state')['armed'])
        self.assertEqual(self.sim.request('health')['api_version'], 1)

    def test_auth(self):
        self.sim.request('health', key='incorrecta')
        self.sim.request('stop', key='incorrecta')
        with self.assertRaises(APIError) as ctx:
            self.sim.request('state', key='incorrecta')
        self.assertEqual(ctx.exception.status, 403)

    def test_challenge_session(self):
        challenge = self.sim.challenge
        self.arm()
        self.assertNotEqual(self.sim.challenge, challenge)
        self.assertGreater(self.session, 0)
        self.sim.request('stop')
        with self.assertRaises(APIError):
            self.sim.request('arm', {'challenge': challenge})

    def test_increasing_sequences_and_busy_consumption(self):
        self.arm()
        self.drive()
        with self.assertRaises(APIError) as ctx:
            self.drive()
        self.assertEqual(ctx.exception.error, 'actuators_busy')
        self.assertEqual(self.sim.request('state')['last_seq'], 2)
        with self.assertRaises(APIError):
            self.sim.request('heartbeat', {'session': self.session, 'seq': 2})

    def test_heartbeat_and_expiry(self):
        self.arm()
        self.clock.advance(1.)
        self.send('heartbeat')
        self.clock.advance(1.)
        self.assertTrue(self.sim.request('state')['armed'])
        self.clock.advance(.21)
        state = self.sim.request('state')
        self.assertFalse(state['armed'])
        self.assertEqual(state['reason'], 'heartbeat_timeout')

    def test_stop_latches_and_invalidates(self):
        self.arm()
        self.drive()
        self.sim.request('stop')
        self.assertFalse(self.sim.request('state')['motor_activo'])
        with self.assertRaises(APIError): self.drive()

    def test_pulse_expiry_deadtime(self):
        self.arm()
        self.drive()
        self.clock.advance(.16)
        self.assertFalse(self.sim.request('state')['motor_activo'])
        with self.assertRaises(APIError): self.drive()
        self.clock.advance(.051)
        self.drive()

    def test_servo_enable_settle_and_motion_interlocks(self):
        self.arm()
        self.send('enable', nombre='garra')
        with self.assertRaises(APIError): self.drive()
        with self.assertRaises(APIError): self.send('enable', nombre='base')
        self.clock.advance(.81)
        self.send('servo', nombre='garra', grado=58)
        with self.assertRaises(APIError): self.drive()
        self.clock.advance(.07)
        self.assertEqual(self.sim.request('state')['garra'], 58)
        self.assertTrue(self.sim.request('state')['brazo_ocupado'])
        self.clock.advance(.21)
        self.drive()

    def test_release_requires_stopped_and_confirmation(self):
        self.arm()
        with self.assertRaises(APIError):
            self.sim.request('release', {'nombre': 'base', 'confirm': 1})
        self.sim.request('stop')
        with self.assertRaises(APIError):
            self.sim.request('release', {'nombre': 'base', 'confirm': 0})
        self.sim.request('release', {'nombre': 'base', 'confirm': 1})

    def test_servo_stop_freezes_goal_preserves_pwm(self):
        self.arm()
        self.send('enable', nombre='base')
        self.clock.advance(.81)
        self.send('servo', nombre='base', grado=100)
        self.clock.advance(.07)
        self.sim.request('stop')
        s = self.sim.request('state')
        self.assertEqual(s['base'], s['base_objetivo'])
        self.assertTrue(s['servo_base_activo'])

    def test_network_failure(self):
        self.sim.online = False
        with self.assertRaises(APIError): self.sim.request('state')

    def test_no_servo_autostart(self):
        self.arm()
        with self.assertRaises(APIError) as ctx:
            self.send('servo', nombre='base', grado=75)
        self.assertEqual(ctx.exception.error, 'servo_not_enabled')
