"""API 1: métodos, formularios, tipos y límites observados en el sketch."""
from app.config import integer, pattern

ROUTES = {'health': ('GET', '/api/health'), 'state': ('GET', '/api/state'),
          'arm': ('POST', '/api/arm'), 'heartbeat': ('POST', '/api/heartbeat'),
          'drive': ('POST', '/api/drive'), 'enable': ('POST', '/api/servo/enable'),
          'servo': ('POST', '/api/servo'), 'stop': ('POST', '/api/stop'),
          'release': ('POST', '/api/release')}
SEQUENCED = {'heartbeat', 'drive', 'enable', 'servo'}


class APIError(Exception):
    def __init__(self, error, status=0):
        self.error, self.status = error, status
        super().__init__(f'HTTP {status}: {error}' if status else error)


def validate_command(action, p):
    expected = {'health': set(), 'state': set(), 'stop': set(), 'arm': {'challenge'},
                'heartbeat': {'session', 'seq'}, 'drive': {'session', 'seq', 'fl', 'fr', 'rl', 'rr', 'ms'},
                'enable': {'session', 'seq', 'nombre'}, 'servo': {'session', 'seq', 'nombre', 'grado'},
                'release': {'nombre', 'confirm'}}
    if action not in expected or set(p) != expected[action]:
        raise ValueError('Parámetros incompatibles con API 1')
    if action in SEQUENCED:
        integer(p['session'], 1, 0xffffffff, 'session')
        integer(p['seq'], 1, 0xffffffff, 'seq')
    if action == 'arm':
        integer(p['challenge'], 1, 0xffffffff, 'challenge')
    if action == 'drive':
        pattern([p[k] for k in ('fl', 'fr', 'rl', 'rr')])
        integer(p['ms'], 50, 700, 'ms')
    if action in ('servo', 'enable', 'release') and p['nombre'] not in ('garra', 'base'):
        raise ValueError('Servo desconocido')
    if action == 'servo':
        integer(p['grado'], 35, 60 if p['nombre'] == 'garra' else 115, 'grado')
    if action == 'release' and p['confirm'] != 1:
        raise ValueError('Confirmación explícita requerida')


def validate_health(data):
    if (data.get('firmware'), data.get('version'), data.get('api_version')) != ('Robot4WD', '1.0.0', 1):
        raise APIError('Firmware incompatible: se requiere Robot4WD 1.0.0 / API 1')


def validate_state(data):
    for key in ('armed', 'maintenance', 'motor_activo', 'brazo_ocupado',
                'servo_garra_activo', 'servo_base_activo'):
        if type(data.get(key)) is not bool:
            raise APIError('Estado inválido: ' + key)
    if data.get('api_version') != 1:
        raise APIError('Versión de estado incompatible')
    for key in ('challenge', 'last_seq', 'garra', 'base', 'garra_objetivo', 'base_objetivo'):
        if type(data.get(key)) is not int:
            raise APIError('Estado inválido: ' + key)
    integer(data['challenge'], 1, 0xffffffff, 'challenge')
    integer(data['last_seq'], 0, 0xffffffff, 'last_seq')
    for name, high in [('garra', 60), ('base', 115)]:
        integer(data[name], 35, high, name)
        integer(data[name + '_objetivo'], 35, high, name)
    directions = data.get('directions')
    if not isinstance(directions, list) or len(directions) != 4:
        raise APIError('Estado inválido: directions')
    for direction in directions:
        integer(direction, -1, 1, 'directions')
    return data
