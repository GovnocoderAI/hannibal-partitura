import math
import random

from .canvas import Canvas
from . import palette as P

W, H = 120, 80
_CACHE = {}


def _base(top, bottom):
    c = Canvas(W, H)
    c.vertical_gradient(0, H, top, bottom)
    return c


def _stone_wall(c, seed=1, tint=(42, 40, 44)):
    rng = random.Random(seed)
    c.vertical_gradient(0, H, (34, 32, 36), (14, 13, 16))
    y = 4
    row = 0
    while y < H:
        x = -10 if row % 2 else 0
        while x < W:
            bw = rng.randint(16, 26)
            bh = rng.randint(7, 10)
            shade = rng.uniform(0.7, 1.25)
            col = (tint[0] * shade, tint[1] * shade, tint[2] * shade)
            c.rect(x + 1, y + 1, x + bw - 1, y + bh - 1, col, 0.5)
            c.stroke([(x, y + bh), (x + bw, y + bh)], 1.0, (10, 9, 11), 0.6, 0.8)
            c.stroke([(x + bw, y), (x + bw, y + bh)], 1.0, (10, 9, 11), 0.5, 0.8)
            x += bw
        y += 9
        row += 1
    c.grain(0.03, seed)


def _light_shaft(c, x0=26, y0=0, x1=118, y1=80, color=(212, 186, 140), a=0.10):
    pts = [(x0, y0), (x0 + 18, y0), (x1, y1), (x1 - 46, y1)]
    c.polygon(pts, color, a, 6.0)


def _candle(c, x, y, h=9, scale=1.0):
    c.rect(x - 1.2 * scale, y - h, x + 1.2 * scale, y, (206, 196, 176), 0.9)
    c.rect(x - 1.2 * scale, y - h, x - 0.2 * scale, y, (168, 158, 140), 0.55)
    c.radial(x, y - h - 2, 9 * scale, (232, 156, 78), 0.22)
    c.ellipse(x, y - h - 1.6, 1.0, 2.4, (248, 196, 108), 0.95, 0.7)
    c.ellipse(x, y - h - 2.2, 0.5, 1.2, (255, 236, 190), 0.9, 0.6)
    c.stroke([(x, y - h + 0.5), (x, y - h - 0.6)], 0.5, (30, 26, 24), 0.9, 0.5)


def _plate(c, x, y, r=6.0):
    c.ellipse(x, y, r, r * 0.34, (228, 222, 208), 0.9, 0.8)
    c.ellipse(x, y - 0.4, r * 0.78, r * 0.24, (208, 200, 184), 0.8, 0.8)
    c.ellipse(x, y - 0.6, r * 0.44, r * 0.14, (150, 58, 52), 0.55, 0.8)
    c.ellipse(x - r * 0.2, y - 0.9, r * 0.2, r * 0.07, (196, 104, 84), 0.5, 0.7)


def _glass(c, x, y, h=8.0, wine=True):
    c.polygon([(x - 2.2, y - h), (x + 2.2, y - h), (x + 1.4, y - h + 4.2), (x - 1.4, y - h + 4.2)], (150, 150, 156), 0.22, 0.7)
    c.stroke([(x - 2.2, y - h), (x + 2.2, y - h)], 0.8, (200, 200, 208), 0.45, 0.6)
    c.stroke([(x - 2.2, y - h), (x - 1.4, y - h + 4.2)], 0.8, (200, 200, 208), 0.35, 0.6)
    c.stroke([(x + 2.2, y - h), (x + 1.4, y - h + 4.2)], 0.8, (200, 200, 208), 0.35, 0.6)
    c.stroke([(x, y - h + 4.2), (x, y - 1.2)], 0.8, (188, 188, 196), 0.4, 0.6)
    c.stroke([(x - 2.6, y - 0.6), (x + 2.6, y - 0.6)], 1.0, (188, 188, 196), 0.45, 0.6)
    if wine:
        c.polygon([(x - 1.8, y - h + 0.8), (x + 1.8, y - h + 0.8), (x + 1.2, y - h + 3.6), (x - 1.2, y - h + 3.6)], (86, 16, 26), 0.85, 0.6)
        c.ellipse(x - 0.6, y - h + 1.4, 0.5, 0.3, (150, 50, 46), 0.5, 0.5)


def _antlers(c, cx=60, cy=28, scale=1.0, color=(58, 50, 42), a=0.85):
    left = [
        [(cx, cy), (cx - 7, cy - 14), (cx - 12, cy - 26)],
        [(cx - 6, cy - 13), (cx - 15, cy - 19), (cx - 19, cy - 27)],
        [(cx - 10, cy - 21), (cx - 8, cy - 30), (cx - 13, cy - 35)],
        [(cx - 12, cy - 25), (cx - 20, cy - 31)],
    ]
    right = [[(2 * cx - x, y) for (x, y) in line] for line in left]
    for line in left + right:
        pts = [(cx + (x - cx) * scale, cy + (y - cy) * scale) for (x, y) in line]
        c.stroke(pts, [2.2 * scale, 1.4 * scale, 0.9 * scale], color, a, 0.9)


def _book_row(c, x, y, width, seed=1):
    rng = random.Random(seed)
    xx = x
    while xx < x + width:
        bw = rng.randint(1, 2)
        bh = rng.randint(4, 9)
        col = rng.choice([(72, 30, 30), (40, 50, 40), (48, 40, 60), (66, 52, 32), (30, 34, 40)])
        c.rect(xx, y - bh, xx + bw - 1, y, col, 0.9)
        c.stroke([(xx, y - bh + 1), (xx, y - bh + 1)], 0.5, (150, 130, 90), 0.5, 0.5)
        xx += bw + 1


def _bookshelf(c, x, y, w, h, seed=1):
    c.rect(x, y, x + w, y + h, (26, 18, 14), 0.95)
    shelves = max(2, h // 12)
    for i in range(shelves + 1):
        sy = y + i * (h // shelves)
        c.rect(x, sy - 0.6, x + w, sy + 0.6, (44, 30, 22), 0.9)
        if i < shelves:
            _book_row(c, x + 2, sy + (h // shelves) - 2, w - 4, seed + i)


def _window(c, x, y, w, h, night=True, snow=False):
    c.rect(x, y, x + w, y + h, (16, 22, 30) if night else (120, 150, 168), 1.0)
    c.rect(x + 1, y + 1, x + w - 1, y + h - 1, (30, 44, 58) if night else (150, 180, 190), 0.7)
    c.stroke([(x + w / 2, y), (x + w / 2, y + h)], 1.4, (20, 18, 18), 0.9, 0.7)
    c.stroke([(x, y + h / 2), (x + w, y + h / 2)], 1.4, (20, 18, 18), 0.9, 0.7)
    c.rect(x - 1, y - 1, x + w + 1, y, (34, 30, 28), 0.9)
    c.rect(x - 1, y + h, x + w + 1, y + h + 1, (34, 30, 28), 0.9)
    if snow:
        rng = random.Random(5)
        for _ in range(70):
            sx = rng.uniform(x + 1, x + w - 1)
            sy = rng.uniform(y + 1, y + h - 1)
            c.ellipse(sx, sy, 0.5, 0.5, (220, 226, 236), rng.uniform(0.4, 0.9), 0.5)


def _lamp_pool(c, x, y, r=18, color=(226, 164, 96), a=0.30):
    c.radial(x, y, r, color, a, 2.0)
    c.ellipse(x, y, 1.8, 1.2, (248, 214, 160), 0.9, 0.7)


def _title():
    c = _base((16, 14, 16), (7, 6, 8))
    c.radial(24, 20, 70, (96, 62, 32), 0.22, 2.2)
    c.radial(98, 26, 50, (40, 48, 64), 0.12, 2.0)
    _antlers(c, 60, 24, 1.35, (46, 38, 32), 0.55)
    c.rect(0, 70, W, H, (12, 10, 11), 0.9)
    c.stroke([(0, 70), (W, 70)], 1.2, (54, 44, 36), 0.6, 1.0)
    _candle(c, 18, 74, 12, 1.2)
    _candle(c, 102, 74, 10, 1.1)
    _glass(c, 32, 78, 9)
    c.vignette(0.6, 1.8)
    c.grain(0.025, 9)
    return c


def _cell():
    c = _base((26, 24, 28), (10, 9, 12))
    _stone_wall(c, 4)
    _light_shaft(c, 18, 0, 96, 80, (196, 178, 140), 0.085)
    c.rect(0, 0, 13, H, (12, 11, 14), 0.55)
    for x in (7, 12):
        c.rect(x, 0, x + 1.4, H, (16, 14, 16), 0.9)
        c.stroke([(x + 0.2, 0), (x + 0.2, H)], 0.6, (92, 86, 78), 0.35, 0.6)
    c.rect(97, 58, 118, 64, (34, 30, 30), 0.85)
    c.rect(98, 56, 117, 58, (46, 40, 38), 0.8)
    c.rect(99, 60, 108, 63, (120, 118, 108), 0.5)
    c.ellipse(104, 61, 5, 1.6, (72, 44, 40), 0.5)
    _candle(c, 100, 61, 4, 0.8)
    rng = random.Random(21)
    for _ in range(16):
        x = rng.uniform(0, 30)
        y = rng.uniform(0, H)
        c.stroke([(x, y), (x + rng.uniform(-3, 3), y + rng.uniform(2, 8))], 0.7, (8, 7, 9), 0.5, 0.8)
    c.vignette(0.6, 1.8)
    c.grain(0.03, 4)
    return c


def _corridor():
    c = _base((20, 20, 24), (8, 8, 10))
    vx, vy = 64, 36
    c.polygon([(0, 0), (0, H), (46, H), (vx - 6, vy + 6), (vx - 6, vy - 6), (46, 0)], (26, 24, 28), 0.9, 1.2)
    c.polygon([(W, 0), (W, H), (74, H), (vx + 6, vy + 6), (vx + 6, vy - 6), (74, 0)], (22, 21, 25), 0.9, 1.2)
    for i in range(5):
        t = i / 5.0
        x0 = int(2 + t * 40)
        x1 = int(112 - t * 40)
        y0 = int(t * 26)
        y1 = int(H - t * 26)
        c.stroke([(x0, y0), (x1, y0)], 0.8, (50, 46, 48), 0.35 - t * 0.05, 0.8)
        c.stroke([(x0, y1), (x1, y1)], 0.8, (50, 46, 48), 0.35 - t * 0.05, 0.8)
    for x, y in ((22, 22), (86, 20)):
        _lamp_pool(c, x, y + 8, 22, (224, 168, 100), 0.16)
        c.rect(x - 3, y, x + 3, y + 2.4, (36, 32, 30), 0.9)
        c.ellipse(x, y + 3, 2.4, 1.0, (238, 196, 132), 0.85, 0.7)
    c.polygon([(0, H), (W, H), (76, 50), (48, 50)], (16, 15, 18), 0.75, 2.0)
    for x in (30, 56, 90, 108):
        c.rect(x, 32, x + 12, 56, (18, 17, 20), 0.7)
        c.stroke([(x + 12, 40), (x + 12, 46)], 0.9, (140, 130, 100), 0.5, 0.6)
    c.vignette(0.55, 1.8)
    c.grain(0.025, 6)
    return c


def _office():
    c = _base((28, 24, 22), (10, 9, 10))
    c.rect(0, 0, 26, H, (20, 14, 12), 0.9)
    _bookshelf(c, 2, 6, 22, 56, 3)
    c.rect(94, 0, W, H, (20, 14, 12), 0.9)
    _bookshelf(c, 96, 6, 22, 56, 7)
    _window(c, 46, 8, 34, 30, True, True)
    _lamp_pool(c, 30, 58, 26, (226, 168, 106), 0.22)
    c.rect(18, 58, 62, 66, (38, 26, 18), 0.95)
    c.rect(18, 56, 62, 58, (54, 38, 26), 0.9)
    c.stroke([(20, 58), (60, 58)], 1.0, (96, 74, 48), 0.4, 0.7)
    c.ellipse(34, 55, 4.2, 1.4, (28, 24, 22), 0.9, 0.7)
    c.stroke([(34, 55), (38, 50)], 1.4, (70, 60, 44), 0.8, 0.6)
    _lamp_pool(c, 39, 49, 16, (236, 182, 112), 0.25)
    c.polygon([(40, 47), (52, 45), (54, 48), (42, 50)], (200, 192, 176), 0.85, 0.7)
    c.polygon([(41, 47.2), (51, 45.4), (52, 46.4), (42, 48.2)], (70, 66, 60), 0.25, 0.6)
    _glass(c, 70, 56, 8)
    c.rect(64, 62, 92, 66, (34, 24, 18), 0.9)
    c.vignette(0.5, 1.8)
    c.grain(0.025, 8)
    return c


def _dinner():
    c = _base((26, 20, 18), (9, 8, 9))
    c.rect(0, 0, W, 44, (22, 16, 14), 0.9)
    for x in range(10, 110, 28):
        c.rect(x, 10, x + 18, 32, (38, 28, 22), 0.55)
        c.stroke([(x + 1, 11), (x + 17, 11)], 0.8, (86, 66, 44), 0.4, 0.7)
    for x in (12, 22, 96, 106):
        _candle(c, x, 42, 10, 1.1)
    c.polygon([(0, 44), (W, 44), (W, H), (0, H)], (58, 44, 34), 0.0, 1.0)
    c.rect(0, 46, W, H, (44, 32, 24), 0.95)
    c.rect(0, 46, W, 48, (96, 76, 52), 0.55)
    _plate(c, 30, 58, 7)
    _plate(c, 60, 56, 8)
    _plate(c, 90, 58, 7)
    _glass(c, 20, 66, 10)
    _glass(c, 44, 68, 9)
    _glass(c, 76, 68, 9)
    _glass(c, 100, 66, 10)
    _candle(c, 50, 64, 12, 1.0)
    _candle(c, 71, 64, 12, 1.0)
    c.radial(60, 60, 46, (232, 168, 100), 0.14, 2.0)
    c.vignette(0.55, 1.7)
    c.grain(0.022, 11)
    return c


def _snow():
    c = _base((18, 22, 30), (8, 10, 14))
    c.rect(0, 0, W, 46, (16, 20, 28), 0.6)
    rng = random.Random(13)
    for i in range(7):
        bx = i * 18 - 6
        bh = rng.randint(24, 42)
        c.rect(bx, 46 - bh, bx + 14, 46, (12, 14, 20), 0.95)
        for wy in range(46 - bh + 4, 42, 7):
            for wx in range(bx + 3, bx + 12, 5):
                if rng.random() < 0.55:
                    c.rect(wx, wy, wx + 2, wy + 2, (206, 168, 96), 0.7)
    c.rect(0, 46, W, 52, (60, 64, 76), 0.35)
    c.rect(0, 50, W, H, (88, 92, 104), 0.45)
    for x in (14, 104):
        c.rect(x, 24, x + 1.2, 58, (24, 22, 24), 0.95)
        c.ellipse(x + 0.6, 24, 3.0, 2.0, (44, 42, 44), 0.95, 0.7)
        _lamp_pool(c, x + 0.6, 26, 20, (240, 190, 120), 0.30)
    c.stroke([(0, 52), (W, 52)], 1.2, (30, 32, 40), 0.7, 1.0)
    for _ in range(160):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        c.ellipse(x, y, 0.45, 0.45, (222, 228, 238), rng.uniform(0.3, 0.85), 0.4)
    c.vignette(0.5, 1.7)
    c.grain(0.02, 14)
    return c


def _house():
    c = _base((26, 20, 18), (9, 8, 9))
    c.rect(0, 0, W, 60, (30, 24, 22), 0.9)
    for x in range(0, W, 6):
        c.stroke([(x, 0), (x, 60)], 0.7, (16, 13, 12), 0.35, 0.7)
    _window(c, 6, 12, 30, 30, True, True)
    c.rect(70, 12, 100, 46, (22, 18, 16), 0.9)
    c.rect(72, 14, 98, 44, (14, 12, 13), 0.95)
    c.ellipse(85, 40, 8, 3.2, (52, 40, 32), 0.9, 0.9)
    c.polygon([(78, 40), (85, 26), (92, 40)], (40, 30, 24), 0.9, 0.8)
    c.radial(85, 38, 26, (232, 140, 70), 0.30, 2.0)
    c.ellipse(85, 39, 5, 1.6, (240, 170, 90), 0.55, 0.9)
    _antlers(c, 85, 22, 0.75, (92, 80, 62), 0.5)
    c.rect(0, 58, W, H, (34, 24, 18), 0.95)
    c.rect(0, 58, W, 60, (66, 48, 32), 0.6)
    _glass(c, 26, 74, 9)
    _candle(c, 108, 76, 10, 1.0)
    c.vignette(0.6, 1.8)
    c.grain(0.025, 17)
    return c


def _memory():
    c = _base((44, 56, 44), (26, 34, 28))
    rng = random.Random(23)
    for _ in range(80):
        x = rng.uniform(0, W)
        y = rng.uniform(0, 52)
        r = rng.uniform(6, 20)
        col = rng.choice([(70, 96, 58), (96, 118, 66), (52, 74, 48)])
        c.ellipse(x, y, r, r * 0.6, col, rng.uniform(0.08, 0.18), 4.0)
    c.ellipse(88, 26, 10, 10, (244, 220, 160), 0.18, 6.0)
    c.rect(0, 54, W, H, (30, 38, 26), 0.9)
    c.vignette(0.55, 1.6)
    c.grain(0.02, 24)
    return c


def _black():
    c = _base((10, 9, 11), (3, 3, 4))
    c.radial(60, 30, 60, (60, 40, 30), 0.08, 2.0)
    c.vignette(0.7, 1.6)
    return c


_BUILDERS = {
    "cell": _cell,
    "corridor": _corridor,
    "office": _office,
    "dinner": _dinner,
    "snow": _snow,
    "house": _house,
    "memory": _memory,
    "black": _black,
    "title": _title,
}


def get_bg(name):
    if name not in _CACHE:
        fn = _BUILDERS.get(name, _black)
        _CACHE[name] = fn()
    return _CACHE[name]
