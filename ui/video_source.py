"""Vista orientada de Camera independiente de la disponibilidad de percepción."""

from app.models import Frame
from ai.transforms import normalize


def original_snapshot(app, snap):
    if not snap["fresh"] or snap["frame"] is None:
        app._original_view_cache = None
        return dict(snap, frame=None, fresh=False)
    f = snap["frame"]
    c = app.config["vision"]
    transform = (c["rotation"], c["flip_horizontal"], c["flip_vertical"])
    key = (id(app.camera), f.generation, f.id, transform)
    cached = getattr(app, "_original_view_cache", None)
    if cached is None or cached[0] != key:
        result = app.vision.snapshot()["result"]
        image = None
        if (
            result
            and result.frame.id == f.id
            and result.frame.generation == f.generation
        ):
            t = result.observation.transform
            if (
                tuple(t[k] for k in ("rotation", "flip_horizontal", "flip_vertical"))
                == transform
            ):
                image = result.normalized
        if image is None:
            image = normalize(f.image, c)
        view = Frame(
            f.id, f.received_at, image, f.fps, f.generation + str(transform), f.source
        )
        cached = app._original_view_cache = (key, view)
    return dict(snap, frame=cached[1])
