"""Percepción visual sin acceso al control o al transporte del robot."""

from dataclasses import dataclass, field, replace
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
    track_id: int | None = None
    confirmed: bool = False
    stable_centroid: tuple | None = None
    valid: bool = True
    reason: str = ""
    extent: float = 0.0
    fill_ratio: float = 0.0


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
    rejected: tuple = ()
    regions: tuple = ()


class Tracker:
    def __init__(self):
        self.previous = None
        self.misses = 0
        self.tracks = {}
        self.next_id = 1
        self.target_id = None
        self.identity = None
        self.current = ()

    def select(self, objects, config, frame=None):
        t = config["tracking"]
        now = time.monotonic()
        if frame is not None and now - frame.received_at > t["max_gap_s"]:
            self.tracks.clear()
            self.current = ()
            self.previous = None
            self.target_id = None
            return None, "Sin objetivo"
        identity = (frame.generation, frame.id) if frame else object()
        repeated = identity == self.identity
        self.identity = identity
        used = set()
        current = []
        for o in objects:
            eligible = [
                (np.linalg.norm(np.subtract(o.position, r["object"].position)), i)
                for i, r in self.tracks.items()
                if i not in used
                and r["object"].color == o.color
                and now - r["seen"] <= t["max_gap_s"]
                and max(o.area, r["object"].area)
                / max(1, min(o.area, r["object"].area))
                <= t["size_ratio_max"]
            ]
            eligible = [
                pair for pair in eligible if pair[0] <= config["tracking_radius"]
            ]
            if eligible:
                _, i = min(eligible)
                r = self.tracks[i]
                if not repeated:
                    r["hits"] = r["hits"] + 1 if r["misses"] == 0 else 1
                stable = tuple(
                    t["smoothing"] * a + (1 - t["smoothing"]) * b
                    for a, b in zip(
                        o.centroid, r["object"].stable_centroid or r["object"].centroid
                    )
                )
            else:
                i = self.next_id
                self.next_id += 1
                r = {"hits": 1, "misses": 0, "seen": now}
                self.tracks[i] = r
                stable = o.centroid
            used.add(i)
            previous_position = r.get("object", o).position
            position = tuple(
                t["smoothing"] * a + (1 - t["smoothing"]) * b
                for a, b in zip(o.position, previous_position)
            )
            tracked = replace(
                o,
                track_id=i,
                confirmed=r["hits"] >= t["confirm_frames"],
                stable_centroid=stable,
                centroid=stable,
                position=position,
                error_x=2 * position[0] - 1,
            )
            r.update(object=tracked, misses=0)
            if not repeated:
                r["seen"] = now
            current.append(tracked)
        for i, r in list(self.tracks.items()):
            if i not in used and not repeated:
                r["misses"] += 1
                r["hits"] = 0
            if r["misses"] > config["lost_frames"] or now - r["seen"] > t["max_gap_s"]:
                del self.tracks[i]
        self.current = tuple(current)
        selected = next(
            (o for o in current if o.track_id == self.target_id and o.confirmed), None
        )
        if selected:
            self.previous = selected
            return selected, "Objetivo seguido"
        if self.target_id in self.tracks:
            self.previous = None
            return None, "Objetivo perdido"
        eligible = [o for o in current if o.confirmed]
        if not eligible:
            self.previous = None
            self.target_id = None
            return None, "Confirmando candidato" if current else "Sin objetivo"
        selected = max(
            eligible, key=lambda o: o.area_ratio * o.quality - 0.1 * abs(o.error_x)
        )
        self.target_id = selected.track_id
        self.previous = selected
        return selected, "Objetivo detectado"


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
        masks, objects, rejected, regions = {}, [], [], []
        search = c["search_roi"]
        rect = search["rect"] if search["enabled"] else [0.0, 0.0, 1.0, 1.0]
        sx, sy, sw, sh = rect
        x0, y0 = int(sx * w), int(sy * h)
        x1, y1 = min(w, int((sx + sw) * w)), min(h, int((sy + sh) * h))
        roi_mask = np.zeros((h, w), np.uint8)
        roi_mask[y0:y1, x0:x1] = 255
        for color, ranges in c["hsv"].items():
            mask = np.zeros((h, w), np.uint8)
            for index, r in enumerate(ranges):
                if not c["interval_meta"][color][index]["enabled"]:
                    continue
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
            masks[color] = cv2.bitwise_and(mask, roi_mask)
        masks["combinada"] = cv2.bitwise_or(
            cv2.bitwise_or(masks["rojo"], masks["verde"]), masks["azul"]
        )
        contours, _ = cv2.findContours(
            masks["combinada"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            area = cv2.contourArea(contour)
            moments = cv2.moments(contour)
            if not moments["m00"]:
                continue
            x, y = moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]
            box = cv2.boundingRect(contour)
            bx, by, bw, bh = box
            stencil = np.zeros((bh, bw), np.uint8)
            local = contour - np.array([[[bx, by]]])
            cv2.drawContours(stencil, [local], -1, 255, -1)
            pixels = max(1, cv2.countNonZero(stencil))
            coverage = {
                color: cv2.countNonZero(
                    cv2.bitwise_and(m[by : by + bh, bx : bx + bw], stencil)
                )
                / pixels
                for color, m in masks.items()
                if color != "combinada"
            }
            colors = [color for color, ratio in coverage.items() if ratio >= 0.15]
            color = colors[0] if len(colors) == 1 else "incierto"
            position = (x / max(1, w - 1), y / max(1, h - 1))
            solidity = min(1.0, area / max(1, cv2.contourArea(cv2.convexHull(contour))))
            extent = area / (bw * bh)
            fill = coverage.get(color, 0.0)
            f = c["filters"]
            reason = []
            if color == "incierto":
                reason.append("Color ambiguo entre categorías")
            if (
                not c["min_area"] <= area <= c["max_area_ratio"] * w * h
                or area / (w * h) < f["min_area_ratio"]
            ):
                reason.append("Área fuera del perfil")
            if bw < f["min_width"] or bh < f["min_height"]:
                reason.append("Dimensiones insuficientes")
            if not f["aspect_min"] <= bw / bh <= f["aspect_max"]:
                reason.append("Relación de aspecto")
            if (
                solidity < f["solidity_min"]
                or extent < f["extent_min"]
                or fill < f["fill_min"]
            ):
                reason.append("Solidez/extensión/proporción de color")
            if f["reject_border"] and (
                bx <= x0 or by <= y0 or bx + bw >= x1 or by + bh >= y1
            ):
                reason.append("Contacto con borde de búsqueda")
            o = ObjectDetection(
                color,
                box,
                (x, y),
                area,
                area / (w * h),
                position,
                2 * position[0] - 1,
                (area / (w * h)) ** 0.5,
                solidity,
                valid=not reason,
                reason="; ".join(reason),
                extent=extent,
                fill_ratio=fill,
            )
            regions.append(o)
            (rejected if reason else objects).append(o)
        masks["combinada"] = cv2.bitwise_or(
            cv2.bitwise_or(masks["rojo"], masks["verde"]), masks["azul"]
        )
        objects.sort(key=lambda o: (o.color, o.box))
        target, state = self.tracker.select(objects, c, frame)
        objects = list(self.tracker.current)
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
        if groups["search"] and search["enabled"]:
            cv2.rectangle(overlay, (x0, y0), (x1 - 1, y1 - 1), (210, 180, 30), 2)
        if groups["regions"]:
            for o in regions:
                x, y, bw, bh = o.box
                cv2.rectangle(
                    overlay, (x, y), (x + bw - 1, y + bh - 1), (180, 180, 180), 1
                )
        if groups["discarded"]:
            for o in rejected:
                x, y, bw, bh = o.box
                cv2.rectangle(
                    overlay, (x, y), (x + bw - 1, y + bh - 1), (130, 130, 130), 1
                )
        if groups["objects"]:
            for o in objects:
                x, y, bw, bh = o.box
                color = PALETTE[o.color]
                cv2.rectangle(overlay, (x, y), (x + bw - 1, y + bh - 1), color, 2)
                cv2.circle(overlay, tuple(round(v) for v in o.centroid), 3, color, -1)
                cv2.putText(
                    overlay,
                    f"{o.color} #{o.track_id}"
                    + (" confirmado" if o.confirmed else " candidato"),
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
            track_id=target.track_id if target else None,
        )
        return Result(
            frame,
            observation,
            normalized,
            image,
            masks,
            overlay,
            tuple(rejected),
            tuple(regions),
        )
