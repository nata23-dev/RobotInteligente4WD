"""Iconos lineales propios, dibujados una vez y reutilizados; sin dependencias nuevas."""

from functools import lru_cache
from PIL import Image, ImageDraw, ImageTk
from ui import theme


@lru_cache(maxsize=128)
def raster(name: str, size: int = 24, color: str = "#426FA8"):
    factor = 3
    image = Image.new("RGBA", (size * factor, size * factor))
    d = ImageDraw.Draw(image)

    def line(points, width=1.7):
        d.line(
            [(x * size * factor / 24, y * size * factor / 24) for x, y in points],
            fill=color,
            width=max(1, round(width * size * factor / 24)),
            joint="curve",
        )

    def box(x1, y1, x2, y2, radius=2):
        k = size * factor / 24
        d.rounded_rectangle(
            (x1 * k, y1 * k, x2 * k, y2 * k),
            radius=radius * k,
            outline=color,
            width=max(1, round(1.7 * k)),
        )

    def circle(x, y, r):
        k = size * factor / 24
        d.ellipse(
            ((x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k),
            outline=color,
            width=max(1, round(1.7 * k)),
        )

    if name in ("robot", "manual"):
        box(3, 8, 21, 19, 4)
        circle(8, 13, 1)
        circle(16, 13, 1)
        line([(9, 16), (15, 16)])
        line([(12, 8), (12, 4)])
        circle(12, 3, 1.5)
        line([(1, 11), (1, 16)])
        line([(23, 11), (23, 16)])
    elif name in ("camera", "video"):
        box(2, 6, 17, 18)
        line([(17, 10), (22, 7), (22, 17), (17, 14)])
    elif name == "dataset":
        for y in (5, 11, 17):
            line([(3, y), (12, y - 3), (21, y), (12, y + 3), (3, y)])
    elif name in ("auto", "gauge"):
        d.arc(
            (
                3 * size * factor / 24,
                3 * size * factor / 24,
                21 * size * factor / 24,
                21 * size * factor / 24,
            ),
            165,
            375,
            fill=color,
            width=max(1, round(size * factor / 14)),
        )
        line([(12, 13), (17, 7)])
        for x, y in ((6, 8), (12, 5), (18, 8)):
            line([(x, y), (x, y + 2)])
    elif name in ("settings", "fuzzy"):
        for y, x in ((6, 9), (12, 16), (18, 7)):
            line([(3, y), (21, y)])
            circle(x, y, 2)
    elif name == "wifi":
        for r in (5, 9, 13):
            k = size * factor / 24
            d.arc(
                ((12 - r) * k, (20 - r) * k, (12 + r) * k, (20 + r) * k),
                220,
                320,
                fill=color,
                width=max(1, round(1.7 * k)),
            )
        circle(12, 19, 1)
    elif name == "shield":
        line([(12, 2), (21, 6), (20, 15), (12, 22), (4, 15), (3, 6), (12, 2)])
        line([(7, 12), (11, 16), (17, 9)])
    elif name == "brain":
        line(
            [
                (11, 21),
                (7, 21),
                (4, 18),
                (4, 15),
                (2, 12),
                (4, 9),
                (4, 6),
                (7, 3),
                (11, 3),
                (11, 21),
            ]
        )
        line(
            [
                (14, 21),
                (18, 20),
                (20, 17),
                (19, 14),
                (22, 11),
                (20, 8),
                (20, 5),
                (17, 2),
                (14, 3),
                (14, 21),
            ]
        )
        line([(5, 9), (8, 10), (8, 14)])
        line([(16, 8), (19, 8)])
        line([(15, 16), (19, 16)])
    elif name == "arm":
        line([(3, 21), (18, 21)])
        box(5, 18, 16, 21)
        line([(9, 18), (6, 11), (13, 4), (20, 9), (19, 13)])
        circle(6, 11, 2)
        circle(13, 4, 2)
        line([(17, 12), (19, 14), (22, 12)])
    elif name == "wheel":
        circle(12, 12, 9)
        circle(12, 12, 3)
        for p in (
            [(12, 3), (12, 7)],
            [(12, 17), (12, 21)],
            [(3, 12), (7, 12)],
            [(17, 12), (21, 12)],
        ):
            line(p)
    elif name == "target":
        circle(12, 12, 9)
        circle(12, 12, 5)
        circle(12, 12, 1)
    elif name == "folder":
        line([(3, 20), (3, 5), (10, 5), (13, 8), (21, 8), (21, 20), (3, 20)])
    elif name == "clock":
        circle(12, 12, 9)
        line([(12, 6), (12, 12), (17, 15)])
    else:
        box(4, 3, 20, 21)
        line([(8, 8), (16, 8)])
        line([(8, 12), (16, 12)])
        line([(8, 16), (14, 16)])
    return image.resize((size, size), Image.Resampling.LANCZOS)


def icon(master, name, size=24, color=None):
    return ImageTk.PhotoImage(
        raster(name, size, color or theme.COLORS["primary"]), master=master
    )
