"""Transformaciones puras BGR: nunca se modifica el original recibido."""
import cv2
import numpy as np


def normalize(image, config):
    rotations = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    out = cv2.rotate(image, rotations[config['rotation']]) if config['rotation'] else image.copy()
    if config['flip_horizontal']: out = cv2.flip(out, 1)
    if config['flip_vertical']: out = cv2.flip(out, 0)
    return out


def digital(image, c):
    out = np.clip(image.astype(np.float32) * c['contrast'] + c['brightness'], 0, 255).astype(np.uint8)
    if c['saturation'] != 1:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * c['saturation'], 0, 255)
        out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    if c['gamma'] != 1:
        lut = np.round(255 * (np.arange(256) / 255) ** (1/c['gamma'])).astype(np.uint8)
        out = cv2.LUT(out, lut)
    if c['sharpness']:
        out = cv2.addWeighted(out, 1+c['sharpness'], cv2.GaussianBlur(out, (3, 3), 0), -c['sharpness'], 0)
    return out


def fit_size(width, height, bounds):
    scale = min(max(1, bounds[0])/width, max(1, bounds[1])/height)
    return max(1, round(width*scale)), max(1, round(height*scale))


def crop_bounds(box, dimensions, margin):
    x, y, w, h = box
    width, height = dimensions
    return (max(0, int(x-w*margin)), max(0, int(y-h*margin)),
            min(width, int(x+w+w*margin+1)), min(height, int(y+h+h*margin+1)))
