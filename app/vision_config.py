"""Perfiles iniciales de software; no constituyen calibración física."""
import copy
import math


def defaults():
    return {
        'rotation': 0, 'flip_horizontal': False, 'flip_vertical': False,
        'digital': {'brightness': 0, 'contrast': 1.0, 'saturation': 1.0, 'gamma': 1.0, 'sharpness': 0.0},
        'hsv': {'rojo': [[0, 90, 60, 10, 255, 255], [170, 90, 60, 179, 255, 255]],
                'verde': [[35, 70, 50, 85, 255, 255]], 'azul': [[90, 80, 50, 135, 255, 255]]},
        'open_kernel': 3, 'close_kernel': 5, 'min_area': 80, 'max_area_ratio': .85,
        'grip_roi': [0.35, 0.65, 0.30, 0.30], 'crop_margin': .12,
        'tracking_radius': .20, 'lost_frames': 4,
        'overlays': {'objects': True, 'target': True, 'axis': True, 'roi': True, 'markers': True},
    }


def dataset_defaults():
    return {'burst_count': 10, 'burst_interval_s': 1.0, 'min_width': 320,
            'min_height': 240, 'dark_mean': 45, 'bright_mean': 215,
            'min_sharpness': 45.0, 'min_object_ratio': .01, 'similarity_distance': 4,
            'reject_exact_duplicates': False}


def number(v, lo, hi, name, integer=False):
    if type(v) not in ((int,) if integer else (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f'{name}: valor entre {lo} y {hi}')


def keys(v, expected, name):
    if not isinstance(v, dict) or set(v) != set(expected):
        raise ValueError(f'{name}: campos inválidos')


def validate(v, d):
    keys(v, defaults(), 'Visión')
    if type(v['rotation']) is not int or v['rotation'] not in (0, 90, 180, 270):
        raise ValueError('Orientación: 0, 90, 180 o 270')
    for k in ('flip_horizontal', 'flip_vertical'):
        if type(v[k]) is not bool: raise ValueError(k + ': booleano requerido')
    keys(v['digital'], defaults()['digital'], 'Ajustes digitales')
    for k, lo, hi in [('brightness', -40, 40), ('contrast', .7, 1.3), ('saturation', .7, 1.3), ('gamma', .7, 1.4), ('sharpness', 0, 1)]:
        number(v['digital'][k], lo, hi, k)
    keys(v['hsv'], defaults()['hsv'], 'HSV')
    for color, ranges in v['hsv'].items():
        if not isinstance(ranges, list) or len(ranges) != (2 if color == 'rojo' else 1): raise ValueError('Intervalos HSV inválidos')
        for r in ranges:
            if not isinstance(r, list) or len(r) != 6: raise ValueError('HSV: seis límites')
            for i, n in enumerate(r): number(n, 0, 179 if i % 3 == 0 else 255, 'HSV', True)
            if any(r[i] > r[i+3] for i in range(3)): raise ValueError('HSV: mínimo mayor que máximo')
    for k in ('open_kernel', 'close_kernel'):
        number(v[k], 1, 15, k, True)
        if v[k] % 2 == 0: raise ValueError('Kernel debe ser impar')
    number(v['min_area'], 1, 1000000, 'Área mínima', True)
    number(v['max_area_ratio'], .01, 1, 'Área máxima relativa')
    roi = v['grip_roi']
    if not isinstance(roi, list) or len(roi) != 4: raise ValueError('ROI: x,y,ancho,alto')
    for n in roi: number(n, 0, 1, 'ROI')
    if roi[2] <= 0 or roi[3] <= 0 or roi[0]+roi[2] > 1 or roi[1]+roi[3] > 1: raise ValueError('ROI fuera de imagen')
    number(v['crop_margin'], 0, .5, 'Margen ROI')
    number(v['tracking_radius'], .01, 1, 'Radio seguimiento')
    number(v['lost_frames'], 1, 30, 'Pérdida temporal', True)
    keys(v['overlays'], defaults()['overlays'], 'Overlays')
    if any(type(b) is not bool for b in v['overlays'].values()): raise ValueError('Overlay: booleano requerido')
    keys(d, dataset_defaults(), 'Dataset')
    for k, lo, hi, i in [('burst_count', 1, 100, True), ('burst_interval_s', .2, 60, False), ('min_width', 1, 4096, True), ('min_height', 1, 4096, True), ('dark_mean', 0, 254, False), ('bright_mean', 1, 255, False), ('min_sharpness', 0, 10000, False), ('min_object_ratio', 0, 1, False), ('similarity_distance', 0, 64, True)]:
        number(d[k], lo, hi, k, i)
    if d['dark_mean'] >= d['bright_mean']: raise ValueError('Umbrales de brillo invertidos')
    if type(d['reject_exact_duplicates']) is not bool: raise ValueError('Duplicados: booleano requerido')


def migrate(config):
    c = copy.deepcopy(config)
    # Solo se migran configuraciones completas del schema previo, nunca campos parciales.
    if 'vision' not in c and 'dataset_options' not in c and 'schema_version' not in c:
        c.update(schema_version=2, vision=defaults(), dataset_options=dataset_defaults())
    return c
