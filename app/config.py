"""Configuración privada, persistencia atómica y límites conservadores."""
import copy
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'config.local.json'
PATTERNS = {
    'adelante': [-1, 1, -1, 1], 'atras': [1, -1, 1, -1],
    'izquierda': [1, 1, -1, -1], 'derecha': [-1, -1, 1, 1],
    'girar_izquierda': [-1, -1, -1, -1], 'girar_derecha': [1, 1, 1, 1],
    'diagonal_frente_izquierda': [-1, 0, 0, 1],
    'diagonal_frente_derecha': [0, 1, -1, 0],
    'diagonal_atras_izquierda': [0, -1, 1, 0],
    'diagonal_atras_derecha': [1, 0, 0, -1],
}


def defaults():
    return {
        'simulation': True, 'robot_url': '', 'camera_url': '', 'api_key': '',
        'timeout_s': 0.18, 'heartbeat_s': 0.25, 'controller_lease_s': 0.65,
        'camera_retry_s': 1.5, 'camera_timeout_ms': 1500, 'frame_max_age_s': 0.8,
        'pulse_ms': 150, 'pulse_min_ms': 50, 'pulse_max_ms': 700,
        'patterns': copy.deepcopy(PATTERNS),
        'servos': {'garra': {'min': 35, 'max': 60, 'home': 60, 'closed': 35},
                   'base': {'min': 35, 'max': 115, 'home': 75}},
        'aruco': {'dictionary': 'DICT_4X4_50', 'cubo': 0, 'cilindro': 1,
                  'prisma_triangular': 2},
        'dataset_dir': 'dataset',
    }


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name}: entero entre {low} y {high}')


def pattern(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('Patrón: FL, FR, RL, RR')
    for direction in value:
        integer(direction, -1, 1, 'Dirección')
    if not any(value):
        raise ValueError('Patrón sin movimiento; para detener use STOP')


def url(value, name, optional=True):
    if not isinstance(value, str):
        raise ValueError(f'{name}: texto requerido')
    if not value and optional:
        return
    p = urlsplit(value)
    if p.scheme != 'http' or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError(f'{name}: URL http:// sin credenciales, consulta ni fragmento')
    try:
        p.port
    except ValueError as exc:
        raise ValueError(f'{name}: puerto inválido') from exc


def validate(c):
    if set(c) != set(defaults()):
        raise ValueError('Faltan campos o hay campos desconocidos en configuración')
    if type(c['simulation']) is not bool:
        raise ValueError('simulation debe ser booleano')
    url(c['robot_url'], 'ESP32')
    if c['robot_url'] and urlsplit(c['robot_url']).path not in ('', '/'):
        raise ValueError('ESP32: indicar solamente origen HTTP')
    url(c['camera_url'], 'Cámara')
    if not isinstance(c['api_key'], str) or (c['api_key'] and not 16 <= len(c['api_key']) <= 64):
        raise ValueError('Clave API: vacía para configurar o de 16 a 64 caracteres')
    for key, low, high in [('timeout_s', .05, .3), ('heartbeat_s', .15, .3),
                          ('controller_lease_s', .4, .8), ('camera_retry_s', .2, 30),
                          ('frame_max_age_s', .1, 5)]:
        v = c[key]
        if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError(f'{key}: valor entre {low} y {high}')
    integer(c['camera_timeout_ms'], 300, 3000, 'Timeout de cámara')
    integer(c['pulse_min_ms'], 50, 700, 'Pulso mínimo')
    integer(c['pulse_max_ms'], c['pulse_min_ms'], 700, 'Pulso máximo')
    integer(c['pulse_ms'], c['pulse_min_ms'], c['pulse_max_ms'], 'Pulso inicial')
    if set(c['patterns']) != set(PATTERNS):
        raise ValueError('Se requieren los diez patrones V7')
    for p in c['patterns'].values():
        pattern(p)
    if set(c['servos']) != {'garra', 'base'}:
        raise ValueError('Se requieren garra y base')
    for name, hardmax in [('garra', 60), ('base', 115)]:
        s = c['servos'][name]
        if set(s) != ({'min', 'max', 'home', 'closed'} if name == 'garra' else {'min', 'max', 'home'}):
            raise ValueError('Campos de servo inválidos')
        integer(s['min'], 35, hardmax, name)
        integer(s['max'], s['min'], hardmax, name)
        integer(s['home'], s['min'], s['max'], name)
        # La activación siempre ordena HOME del firmware; no puede ocultarse con límites menores.
        if s['home'] != (60 if name == 'garra' else 75):
            raise ValueError('HOME debe coincidir con el firmware: garra 60°, base 75°')
        if name == 'garra':
            integer(s['closed'], s['min'], s['max'], name)
    if c['aruco'] != defaults()['aruco']:
        raise ValueError('Destinos fase 01: DICT_4X4_50 / cubo 0, cilindro 1, prisma 2')
    if not isinstance(c['dataset_dir'], str) or not c['dataset_dir'].strip():
        raise ValueError('Directorio de dataset requerido')
    return copy.deepcopy(c)


def load(path=LOCAL):
    return validate(json.loads(Path(path).read_text(encoding='utf-8'))) if Path(path).exists() else defaults()


def save(c, path=LOCAL):
    valid = validate(c)
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(valid, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)
