"""Muestreo robusto y propuestas experimentales; sin escrituras ni autoridad de control."""

import copy
import cv2
import numpy as np
from app.vision_config import check_roi


def overlaps(config):
    result = []
    colors = list(config["hsv"])
    for i, a in enumerate(colors):
        for b in colors[i + 1 :]:
            for j, r in enumerate(config["hsv"][a]):
                for k, s in enumerate(config["hsv"][b]):
                    if (
                        config["interval_meta"][a][j]["enabled"]
                        and config["interval_meta"][b][k]["enabled"]
                        and all(
                            max(r[n], s[n]) <= min(r[n + 3], s[n + 3]) for n in range(3)
                        )
                    ):
                        result.append((a, j, b, k))
    return result


def sample_region(image, rect):
    check_roi(list(rect))
    h, w = image.shape[:2]
    x, y, rw, rh = rect
    crop = image[
        int(y * h) : max(int(y * h) + 1, int((y + rh) * h)),
        int(x * w) : max(int(x * w) + 1, int((x + rw) * w)),
    ]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    selected = hsv[
        (hsv[:, 1] >= 40) & (hsv[:, 2] >= 20) & ~((hsv[:, 2] >= 250) & (hsv[:, 1] < 90))
    ]
    if len(selected) < 8:
        raise ValueError(
            "Muestra insuficiente: seleccione más color y menos reflejos/fondo sin saturación"
        )
    # Centro circular: evita que rojo 0/179 se convierta en verde por mediana lineal.
    angle = selected[:, 0].astype(float) * 2 * np.pi / 180
    center = (
        np.arctan2(np.sin(angle).mean(), np.cos(angle).mean()) * 180 / (2 * np.pi)
    ) % 180
    hue_delta = (selected[:, 0].astype(float) - center + 90) % 180 - 90
    lo, hi = np.percentile(hue_delta, [5, 95])
    lo += center - 3
    hi += center + 3
    s0, v0 = np.maximum(
        [30, 15], np.percentile(selected[:, 1:], [5], axis=0)[0] - 15
    ).astype(int)
    s1, v1 = np.minimum(
        255, np.percentile(selected[:, 1:], [95], axis=0)[0] + 15
    ).astype(int)
    if hi - lo >= 179:
        ranges = [[0, int(s0), int(v0), 179, int(s1), int(v1)]]
    else:
        low = int(np.floor(lo)) % 180
        high = int(np.ceil(hi)) % 180
        ranges = (
            [
                [low, int(s0), int(v0), 179, int(s1), int(v1)],
                [0, int(s0), int(v0), high, int(s1), int(v1)],
            ]
            if low > high
            else [[low, int(s0), int(v0), high, int(s1), int(v1)]]
        )
    return {
        "pixels_total": len(hsv),
        "pixels_used": len(selected),
        "hue_center": float(center),
        "median_hsv": [
            float((center + np.median(hue_delta)) % 180),
            *np.median(selected[:, 1:], axis=0).tolist(),
        ],
        "hue_p05_p95_unwrapped": [float(lo + 3), float(hi - 3)],
        "median_sv": np.median(selected[:, 1:], axis=0).tolist(),
        "p05": np.percentile(selected, [5], axis=0)[0].tolist(),
        "p95": np.percentile(selected, [95], axis=0)[0].tolist(),
        "hue_dispersion": float(np.std(hue_delta)),
        "ranges": ranges,
        "rect": list(rect),
    }


def append_sample(config, color, sample, name):
    if color not in config["hsv"]:
        raise ValueError("Color inválido")
    result = copy.deepcopy(config)
    if len(result["hsv"][color]) + len(sample["ranges"]) > 16:
        raise ValueError("Máximo 16 intervalos por color")
    result["hsv"][color].extend(copy.deepcopy(sample["ranges"]))
    result["interval_meta"][color].extend(
        {"name": name + f" {i+1}", "enabled": True}
        for i in range(len(sample["ranges"]))
    )
    return result


def display_rect(start, end, image_shape, display_size):
    """Coordenadas sobre el label de imagen, sin incluir sus bandas laterales."""
    w, h = display_size
    x0, x1 = sorted((max(0, min(w, start[0])), max(0, min(w, end[0]))))
    y0, y1 = sorted((max(0, min(h, start[1])), max(0, min(h, end[1]))))
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise ValueError("Seleccione una región de al menos dos píxeles de pantalla")
    return [x0 / w, y0 / h, (x1 - x0) / w, (y1 - y0) / h]
