"""Percepción visual sin acceso al control o al transporte del robot."""

from dataclasses import dataclass, field
import copy
import time
import cv2
import numpy as np
from app.models import Observation
from ai.transforms import normalize, digital

STATIONS = {0: "Cubos", 1: "Cilindros", 2: "Prismas triangulares"}
PALETTE = {"rojo": (40, 45, 225), "verde": (60, 175, 55), "azul": (230, 125, 30)}


@dataclass(frozen=True)
class ObjectDetection:
    color: str
    box: tuple
    centroid: tuple
    area: float
    area_ratio: float
    position: tuple
    error_x: float
    apparent_size: float
    quality: float


@dataclass(frozen=True)
class Marker:
    id: int
    corners: tuple
    center: tuple
    apparent_size: float
    position: tuple
    error_x: float
    station: str | None
    valid: bool = True


@dataclass(frozen=True)
class Result:
    frame: object
    observation: Observation
    normalized: np.ndarray = field(repr=False)
    processing: np.ndarray = field(repr=False)
    masks: dict = field(repr=False)
    overlay: np.ndarray = field(repr=False)


class Tracker:
    def __init__(self):
        self.previous = None
        self.misses = 0

    def select(self, objects, config):
        if self.previous:
            eligible = [
                o
                for o in objects
                if o.color == self.previous.color
                and np.linalg.norm(np.subtract(o.position, self.previous.position))
                <= config["tracking_radius"]
            ]
            if eligible:
                target = min(
                    eligible,
                    key=lambda o: np.linalg.norm(
                        np.subtract(o.position, self.previous.position)
                    ),
                )
                self.previous, self.misses = target, 0
                return target, "Objetivo seguido"
            self.misses += 1
            if self.misses <= config["lost_frames"]:
                return None, "Objetivo perdido"
            self.previous = None
        if not objects:
            return None, "Sin objetivo"
        target = max(
            objects, key=lambda o: o.area_ratio * o.quality - 0.10 * abs(o.error_x)
        )
        self.previous, self.misses = target, 0
        return target, "Objetivo detectado"


class Perception:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.tracker = Tracker()
        self.generation = None
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.detector = cv2.aruco.ArucoDetector(dictionary)

    def process(self, frame):
        started = time.perf_counter()
        c = self.config
        if self.generation != frame.generation:
            self.tracker = Tracker()
            self.generation = frame.generation
        normalized = normalize(frame.image, c)
        image = digital(normalized, c["digital"])
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        masks, objects = {}, []
        for color, ranges in c["hsv"].items():
            mask = np.zeros((h, w), np.uint8)
            for r in ranges:
                mask = cv2.bitwise_or(
                    mask, cv2.inRange(hsv, np.array(r[:3]), np.array(r[3:]))
                )
            for operation, size in (
                (cv2.MORPH_OPEN, c["open_kernel"]),
                (cv2.MORPH_CLOSE, c["close_kernel"]),
            ):
                mask = cv2.morphologyEx(
                    mask, operation, np.ones((size, size), np.uint8)
                )
            masks[color] = mask
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                area = cv2.contourArea(contour)
                if not c["min_area"] <= area <= c["max_area_ratio"] * w * h:
                    continue
                moments = cv2.moments(contour)
                if not moments["m00"]:
                    continue
                x, y = moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]
                box = cv2.boundingRect(contour)
                position = (x / max(1, w - 1), y / max(1, h - 1))
                objects.append(
                    ObjectDetection(
                        color,
                        box,
                        (x, y),
                        area,
                        area / (w * h),
                        position,
                        2 * position[0] - 1,
                        (area / (w * h)) ** 0.5,
                        min(
                            1.0, area / max(1, cv2.contourArea(cv2.convexHull(contour)))
                        ),
                    )
                )
        masks["combinada"] = cv2.bitwise_or(
            cv2.bitwise_or(masks["rojo"], masks["verde"]), masks["azul"]
        )
        objects.sort(key=lambda o: (o.color, o.box))
        target, state = self.tracker.select(objects, c)
        corners, ids, _ = self.detector.detectMarkers(normalized)
        markers = []
        if ids is not None:
            for points, marker_id in zip(corners, ids.flatten()):
                pts = points.reshape(4, 2)
                x, y = pts.mean(axis=0)
                position = float(x / max(1, w - 1)), float(y / max(1, h - 1))
                markers.append(
                    Marker(
                        int(marker_id),
                        tuple(tuple(float(v) for v in p) for p in pts),
                        (float(x), float(y)),
                        float(cv2.arcLength(pts, True) / 4),
                        position,
                        2 * position[0] - 1,
                        STATIONS.get(int(marker_id)),
                    )
                )
        overlay = image.copy()
        groups = c["overlays"]
        if groups["objects"]:
            for o in objects:
                x, y, bw, bh = o.box
                color = PALETTE[o.color]
                cv2.rectangle(overlay, (x, y), (x + bw - 1, y + bh - 1), color, 2)
                cv2.circle(overlay, tuple(round(v) for v in o.centroid), 3, color, -1)
                cv2.putText(
                    overlay,
                    o.color,
                    (x, max(15, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                    cv2.LINE_AA,
                )
        if groups["target"] and target:
            cv2.circle(
                overlay, tuple(round(v) for v in target.centroid), 12, (0, 235, 255), 2
            )
        if groups["axis"]:
            cv2.line(overlay, (w // 2, 0), (w // 2, h - 1), (150, 150, 150), 1)
        if groups["roi"]:
            x, y, rw, rh = c["grip_roi"]
            cv2.rectangle(
                overlay,
                (int(x * w), int(y * h)),
                (min(w - 1, int((x + rw) * w)), min(h - 1, int((y + rh) * h))),
                (100, 185, 215),
                1,
            )
        if groups["markers"]:
            for m in markers:
                pts = np.array(m.corners, np.int32)
                cv2.polylines(overlay, [pts], True, (210, 90, 170), 2)
                text = f'ID {m.id} {m.station or "desconocido"}'
                tw, th = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
                location = (
                    max(0, min(w - tw - 2, int(pts[0, 0]))),
                    max(th + 2, int(pts[0, 1]) - 4),
                )
                cv2.putText(
                    overlay,
                    text,
                    location,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (160, 60, 155),
                    1,
                    cv2.LINE_AA,
                )
        observation = Observation(
            frame_id=frame.id,
            color=target.color if target else None,
            alignment_error=target.error_x if target else None,
            proximity=target.apparent_size if target else None,
            stage="Solo percepción; autonomía bloqueada",
            generation=frame.generation,
            received_at=frame.received_at,
            dimensions=(w, h),
            transform=copy.deepcopy(c),
            processing_ms=(time.perf_counter() - started) * 1000,
            objects=tuple(objects),
            markers=tuple(markers),
            target=target,
            tracking_state=state,
        )
        return Result(frame, observation, normalized, image, masks, overlay)
