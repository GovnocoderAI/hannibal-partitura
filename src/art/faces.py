import math
import random
from dataclasses import dataclass, field

from .canvas import Canvas, clamp, smoothstep, sd_ellipse, sd_polygon, sd_segment, mix_color
from . import palette as P

W, H = 120, 80
CX = 60.0
EYE_Y = 27.0
BROW_Y = 20.0
NOSE_Y = 38.5
MOUTH_Y = 45.0
CHIN_Y = 55.5
EYE_DX = 11.6


@dataclass
class FaceStyle:
    name: str = "hannibal"
    skin_base: tuple = P.SKIN_BASE
    skin_light: tuple = P.SKIN_LIGHT
    skin_shadow: tuple = P.SKIN_SHADOW
    skin_deep: tuple = P.SKIN_DEEP
    hair_base: tuple = P.HAIR_BASE
    hair_light: tuple = P.HAIR_LIGHT
    hair_shadow: tuple = P.HAIR_DARK
    iris: tuple = P.IRIS_AMBER
    lip_base: tuple = P.LIP_BASE
    lip_light: tuple = P.LIP_LIGHT
    lip_dark: tuple = P.LIP_DARK
    suit: tuple = P.SUIT
    suit_light: tuple = P.SUIT_LIGHT
    shirt: tuple = P.SHIRT
    tie: tuple = P.TIE
    head_w: float = 46.0
    head_h: float = 52.0
    jaw: float = 1.12
    cheek: float = 1.0
    lip_full: float = 1.0
    brow_thick: float = 2.4
    age: float = 0.9
    hair_style: str = "slick"
    beard: float = 0.05
    mustache: float = 0.0
    glasses: bool = False
    glasses_color: tuple = (150, 130, 90)
    eyes_hooded: float = 0.55
    eye_color_ring: tuple = (40, 24, 14)
    ear_visible: float = 1.0
    scars: tuple = ()


EXPRESSIONS = {
    "neutral": dict(brow=(0.0, 0.0), brow_tilt=0.0, eye_open=1.0, mouth="closed", smile=0.05, tint=0.0, gaze=(0, 0)),
    "warm": dict(brow=(0.6, 0.3), brow_tilt=-1.0, eye_open=0.86, mouth="smile", smile=0.55, tint=0.10, gaze=(0, 0)),
    "amused": dict(brow=(0.9, 0.1), brow_tilt=-1.6, eye_open=0.78, mouth="smirk", smile=0.72, tint=0.05, gaze=(1, 0)),
    "predatory": dict(brow=(-0.9, -0.4), brow_tilt=2.2, eye_open=0.62, mouth="closed", smile=0.25, tint=-0.10, gaze=(0, 0), glint=True),
    "cold": dict(brow=(-0.3, -0.3), brow_tilt=0.6, eye_open=0.88, mouth="grim", smile=-0.15, tint=-0.16, gaze=(0, 0)),
    "intimate": dict(brow=(0.4, 0.5), brow_tilt=0.4, eye_open=0.52, mouth="parted", smile=0.30, tint=0.14, gaze=(0, 1)),
    "pain": dict(brow=(1.6, -0.6), brow_tilt=-3.2, eye_open=0.35, mouth="teeth", smile=-0.30, tint=-0.12, gaze=(0, -1)),
    "bloody": dict(brow=(0.2, 0.2), brow_tilt=1.2, eye_open=1.05, mouth="grin", smile=0.45, tint=-0.05, gaze=(0, 0), glint=True, blood=True),
    "closed": dict(brow=(0.0, 0.0), brow_tilt=-0.2, eye_open=0.0, mouth="closed", smile=0.28, tint=0.06, gaze=(0, 0)),
    "hungry": dict(brow=(-1.2, 0.6), brow_tilt=2.8, eye_open=0.9, mouth="open", smile=0.2, tint=0.02, gaze=(0, 0), glint=True),
    "smile_talk": dict(brow=(0.8, 0.3), brow_tilt=-0.8, eye_open=0.82, mouth="talk", smile=0.6, tint=0.08, gaze=(0, 0)),
}


def _hash_noise(x, y, seed=0):
    n = (x * 374761393 + y * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0 - 0.5


class Portrait:
    def __init__(self, style):
        self.s = style
        self.base = None
        self._cache = {}
        self._build()

    def _face_sdf_fn(self):
        s = self.s
        cx, cy = CX, EYE_Y + 2.0
        rx = s.head_w * 0.5
        ry = s.head_h * 0.5
        jaw = s.jaw
        pts = [
            (cx - rx * 0.92, cy - ry * 0.25),
            (cx - rx * 0.97, cy + ry * 0.10),
            (cx - rx * 0.82, cy + ry * 0.52),
            (cx - rx * 0.58 * jaw, cy + ry * 0.80),
            (cx - rx * 0.28 * jaw, cy + ry * 0.98),
            (cx, cy + ry * 1.06),
            (cx + rx * 0.28 * jaw, cy + ry * 0.98),
            (cx + rx * 0.58 * jaw, cy + ry * 0.80),
            (cx + rx * 0.82, cy + ry * 0.52),
            (cx + rx * 0.97, cy + ry * 0.10),
            (cx + rx * 0.92, cy - ry * 0.25),
        ]

        def f(x, y):
            d1 = sd_ellipse(x, y, cx, cy, rx, ry)
            d2 = sd_polygon(x, y, pts)
            return min(d1, d2)

        return f

    def _skin_shade(self, x, y, sdf):
        s = self.s
        cx, cy = CX, EYE_Y + 2.0
        rx = s.head_w * 0.5
        ry = s.head_h * 0.5
        nx = (x - cx) / rx
        ny = (y - cy) / ry
        nz = math.sqrt(max(0.04, 1.0 - nx * nx * 0.85 - ny * ny * 0.75))
        Lx, Ly, Lz = -0.47, -0.68, 0.56
        lam = clamp(nx * Lx + ny * Ly + nz * Lz, 0.0, 1.0)
        fill = clamp(nx * 0.75 + ny * 0.05 + nz * 0.45, 0.0, 1.0)
        v = 0.20 + 0.92 * lam + 0.30 * fill
        rim = clamp((nx * 0.85 - ny * 0.15), 0.0, 1.0) ** 5
        ao = 0.0
        for (ox, oy, orx, ory, k) in (
            (CX - EYE_DX, EYE_Y + 0.8, 9.0, 5.2, 0.22),
            (CX + EYE_DX, EYE_Y + 0.8, 9.0, 5.2, 0.22),
            (CX, NOSE_Y - 3.0, 4.2, 7.0, 0.10),
            (CX, MOUTH_Y + 4.0, 8.0, 3.5, 0.13),
            (CX, CHIN_Y - 1.0, 10.0, 5.0, 0.10),
        ):
            d = math.hypot((x - ox) / orx, (y - oy) / ory)
            if d < 1.0:
                ao += k * (1.0 - d) ** 1.6
        if y < 15.5:
            ao += 0.28 * smoothstep(15.5, 8.0, y)
        ao += 0.16 * smoothstep(CHIN_Y - 3.0, CHIN_Y + 3.0, y)
        v *= 1.0 - clamp(ao, 0.0, 0.65)
        v += _hash_noise(int(x), int(y), 11) * 0.012

        t = clamp(v, 0.0, 1.3)
        col = mix_color(s.skin_deep, s.skin_shadow, clamp(t * 2.6, 0.0, 1.0))
        col = mix_color(col, s.skin_base, clamp((t - 0.34) * 2.4, 0.0, 1.0))
        col = mix_color(col, s.skin_light, clamp((t - 0.86) * 1.7, 0.0, 1.0))

        warmth = 0.0
        for (ox, oy, r, k) in (
            (CX - 15.0, EYE_Y + 9.0, 8.5, 0.16),
            (CX + 15.0, EYE_Y + 9.0, 8.5, 0.16),
            (CX, NOSE_Y + 1.0, 5.5, 0.20),
            (CX, BROW_Y - 2.0, 8.0, 0.10),
        ):
            d = math.hypot(x - ox, y - oy) / r
            if d < 1.0:
                warmth += k * (1.0 - d) ** 2
        if warmth > 0:
            col = mix_color(col, (232, 150, 132), clamp(warmth, 0.0, 0.35))

        if rim > 0.0:
            col = mix_color(col, (206, 178, 148), rim * 0.30)

        if s.beard > 0.0:
            bm = 0.0
            if y > EYE_Y + 10.0:
                jawd = math.hypot((x - CX) / (rx * 0.92), (y - (CHIN_Y - 2.0)) / (ry * 0.55))
                bm = clamp(1.3 - jawd, 0.0, 1.0)
            if EYE_Y + 12.0 < y < MOUTH_Y + 2.5 and abs(x - CX) < 9.0:
                bm = max(bm, 0.55)
            if bm > 0.0:
                col = mix_color(col, (92, 88, 104), bm * s.beard * 0.55)
                col = mix_color(col, (60, 54, 64), bm * s.beard * 0.25 * (0.5 + _hash_noise(int(x), int(y), 5)))

        return col

    def _build(self):
        s = self.s
        c = Canvas(W, H, (0, 0, 0, 0))
        self._draw_suit(c)
        self._draw_neck(c)
        self._draw_head(c)
        self._draw_ears(c)
        self._draw_hair(c)
        self._draw_static_details(c)
        self._draw_glasses(c)
        for (x, y, w, h, col, a) in s.scars:
            c.stroke([(x, y), (x + w, y + h)], 1.0, col, a, feather=0.8)
        self.base = c

    def _skin_at(self, x, y):
        col = self.base.get(int(x), int(y))
        if col[3] < 0.5:
            return tuple(int(v) for v in self.s.skin_base)
        return tuple(int(clamp(v, 0, 255)) for v in col[:3])

    def _draw_head(self, c):
        s = self.s
        f = self._face_sdf_fn()
        x0 = int(CX - s.head_w * 0.62 - 4)
        x1 = int(CX + s.head_w * 0.62 + 4)
        y0 = int(EYE_Y - s.head_h * 0.58 - 2)
        y1 = int(EYE_Y + 2.0 + s.head_h * 0.62 + 4)
        p = c.px
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                d = f(x + 0.5, y + 0.5)
                if d > 1.4:
                    continue
                cov = clamp(0.5 - d / 0.9, 0.0, 1.0)
                if cov <= 0.01:
                    continue
                col = self._skin_shade(x, y, d)
                i = (y * W + x) * 4
                da = p[i + 3]
                sa = cov
                na = sa + da * (1.0 - sa)
                p[i] = (col[0] * sa + p[i] * da * (1.0 - sa)) / na
                p[i + 1] = (col[1] * sa + p[i + 1] * da * (1.0 - sa)) / na
                p[i + 2] = (col[2] * sa + p[i + 2] * da * (1.0 - sa)) / na
                p[i + 3] = na

    def _draw_neck(self, c):
        s = self.s
        pts = [(52, 46), (68, 46), (72, 80), (48, 80)]
        c.polygon(pts, s.skin_shadow, 1.0, feather=1.0)
        c.polygon([(53, 46), (60, 48), (60, 80), (52, 80)], P.mix(s.skin_shadow, s.skin_deep, 0.25), 1.0, 1.2)
        c.ellipse(CX, 57.0, 15.0, 6.0, s.skin_deep, 0.45, feather=4.0)

    def _draw_suit(self, c):
        s = self.s
        pts = [(-4, 80), (2, 72), (14, 67), (28, 63.5), (42, 62.5), (50, 63.5), (70, 63.5), (78, 62.5), (92, 63.5), (106, 67), (118, 72), (124, 80)]
        c.polygon(pts, s.suit, 1.0, feather=0.8)
        c.stroke([(50, 63.5), (36, 69), (24, 78)], 1.6, s.suit_light, 0.55, feather=1.0)
        c.stroke([(70, 63.5), (84, 69), (96, 78)], 1.6, s.suit_light, 0.40, feather=1.0)
        c.polygon([(48, 64), (60, 78), (72, 64), (66, 62.5), (54, 62.5)], s.shirt, 1.0, feather=0.8)
        c.polygon([(47, 64), (54.5, 62.8), (53, 68)], s.shirt, 1.0, feather=0.7)
        c.polygon([(73, 64), (65.5, 62.8), (67, 68)], s.shirt, 1.0, feather=0.7)
        c.stroke([(47, 64), (54, 63)], 1.0, (150, 144, 134), 0.7, feather=0.8)
        c.stroke([(73, 64), (66, 63)], 1.0, (150, 144, 134), 0.7, feather=0.8)
        c.polygon([(57.6, 64.5), (62.4, 64.5), (63.6, 80), (56.4, 80)], s.tie, 1.0, feather=0.8)
        c.stroke([(58.6, 65), (58.0, 79)], 1.0, P.mix(s.tie, (120, 40, 40), 0.35), 0.5, feather=0.8)
        c.stroke([(59, 64.5), (60, 63.5)], 1.0, (12, 10, 12), 0.8, feather=0.7)

    def _draw_ears(self, c):
        s = self.s
        if s.ear_visible <= 0.0:
            return
        for side in (-1, 1):
            ex = CX + side * (s.head_w * 0.5 + 1.0)
            ey = EYE_Y + 3.0
            c.ellipse(ex, ey, 3.4, 7.6, s.skin_shadow, 0.9 * s.ear_visible, feather=0.9)
            c.ellipse(ex, ey + 0.6, 2.1, 5.2, P.mix(s.skin_shadow, s.skin_deep, 0.35), 0.75 * s.ear_visible, feather=0.8)
            c.ellipse(ex - side * 0.4, ey + 1.2, 1.0, 3.4, P.mix(s.skin_deep, (50, 30, 26), 0.4), 0.7, feather=0.8)
            c.ellipse(ex + side * 0.8, ey - 2.5, 1.2, 2.2, s.skin_light, 0.35, feather=0.9)

    def _hair_cap_points(self):
        s = self.s
        style = s.hair_style
        if style == "bald_top":
            return [
                (33, 26), (32, 17), (35, 12), (41, 9), (46, 8), (48, 12), (52, 10), (58, 9),
                (62, 9), (68, 10), (73, 12), (76, 9), (81, 10), (86, 14), (88, 20), (87, 26),
                (83, 23), (80, 18), (74, 14), (68, 12), (61, 11), (54, 12), (47, 14), (41, 18), (37, 23),
            ]
        if style == "long":
            return [
                (31, 30), (31, 14), (36, 6), (46, 1), (60, -1), (74, 1), (84, 6), (89, 14),
                (89, 34), (85, 28), (82, 18), (76, 12), (68, 9), (64, 12), (60, 10), (56, 12),
                (52, 9), (44, 12), (38, 18), (35, 28),
            ]
        return [
            (33, 26), (32, 17), (36, 9), (44, 4), (53, 1.5), (67, 1.5), (76, 4), (84, 9),
            (88, 17), (87, 26), (83, 23), (79, 17), (73, 11), (67, 9), (63, 12), (60, 14),
            (57, 12), (53, 9), (47, 11), (41, 17), (37, 23),
        ]

    def _hair_side_points(self):
        return [
            [(32, 22), (37, 14), (40, 20), (40, 34), (36, 36), (33, 32)],
            [(88, 22), (83, 14), (80, 20), (80, 34), (84, 36), (87, 32)],
        ]

    def _draw_hair(self, c):
        s = self.s
        cap = self._hair_cap_points()
        c.polygon(cap, s.hair_base, 1.0, feather=0.9)
        c.ellipse(CX, 6.0, s.head_w * 0.5 + 3.0, 8.0, s.hair_base, 0.9, feather=2.0)
        for side_pts in self._hair_side_points():
            c.polygon(side_pts, s.hair_shadow, 1.0, feather=0.9)
        edge = [(37, 23), (41, 15), (48, 10), (56, 12), (60, 14), (64, 12), (72, 10), (79, 15), (83, 23)]
        c.stroke(edge, 2.2, s.hair_shadow, 0.85, feather=1.2)
        c.stroke([(p[0], p[1] - 1.4) for p in edge], 1.0, s.hair_light, 0.30, feather=1.0)

        rng = random.Random(hash(s.name) & 0xFFFF)
        for i in range(14):
            t = i / 13.0
            x = 36 + t * 48
            y = 24.0 - math.sin(t * math.pi) * 11.0
            x2 = x + rng.uniform(-3.0, 3.0)
            y2 = y - rng.uniform(4.0, 9.0)
            x3 = x2 + rng.uniform(-2.0, 2.0)
            y3 = y2 - rng.uniform(3.0, 6.0)
            c.stroke([(x, y), (x2, y2), (x3, y3)], 0.9, s.hair_light, 0.16 + rng.random() * 0.20, feather=0.9)
        c.stroke([(34, 20), (38, 10), (48, 3.5), (60, 2.0), (72, 3.5), (82, 10), (86, 20)], 1.2, s.hair_light, 0.55, feather=1.2)
        c.stroke([(34, 21), (37, 12), (46, 5), (58, 3)], 0.8, (140, 112, 84), 0.35, feather=1.0)
        if s.hair_style == "long":
            c.polygon([(30, 20), (34, 12), (36, 40), (33, 62), (28, 58), (28, 34)], s.hair_shadow, 1.0, 1.0)
            c.polygon([(90, 20), (86, 12), (84, 40), (87, 62), (92, 58), (92, 34)], s.hair_shadow, 1.0, 1.0)
            c.stroke([(32, 24), (31, 42), (33, 58)], 1.0, s.hair_light, 0.3, 1.0)
            c.stroke([(88, 24), (89, 42), (87, 58)], 1.0, s.hair_light, 0.25, 1.0)
        if s.hair_style == "bald_top":
            c.ellipse(CX, 9.0, s.head_w * 0.42, 5.0, s.skin_light, 0.25, 1.4)

    def _draw_static_details(self, c):
        s = self.s
        a = s.age
        c.stroke([(50.5, 40.0), (49.6, 44.0), (50.4, 46.5)], 1.0, s.skin_deep, 0.16 * a, feather=1.1)
        c.stroke([(69.5, 40.0), (70.4, 44.0), (69.6, 46.5)], 1.0, s.skin_deep, 0.16 * a, feather=1.1)
        c.stroke([(52, 13.2), (60, 12.2), (68, 13.2)], 0.9, s.skin_deep, 0.10 * a, feather=1.0)
        c.stroke([(52.5, 16.0), (60, 15.2), (67.5, 16.0)], 0.8, s.skin_deep, 0.07 * a, feather=1.0)
        for side in (-1, 1):
            ex = CX + side * EYE_DX
            c.stroke([(ex + side * 6.0, EYE_Y - 1.0), (ex + side * 8.4, EYE_Y - 2.4)], 0.8, s.skin_deep, 0.10 * a, 0.9)
            c.stroke([(ex + side * 6.2, EYE_Y + 1.2), (ex + side * 8.6, EYE_Y + 2.4)], 0.8, s.skin_deep, 0.08 * a, 0.9)
        c.ellipse(CX, 39.2, 3.0, 1.7, s.skin_light, 0.30, 1.0)
        c.stroke([(56.6, 40.2), (56.0, 39.0)], 0.8, s.skin_deep, 0.5, 0.7)
        c.stroke([(63.4, 40.2), (64.0, 39.0)], 0.8, s.skin_deep, 0.5, 0.7)
        c.ellipse(CX, CHIN_Y - 1.2, 7.0, 2.2, s.skin_light, 0.14, 2.0)
        if s.mustache > 0.0:
            c.ellipse(CX, MOUTH_Y - 3.2, 9.2, 2.0, s.hair_shadow, 0.9 * s.mustache, 0.8)
            c.ellipse(CX, MOUTH_Y - 2.6, 7.6, 1.1, s.hair_light, 0.25 * s.mustache, 0.8)

    def _draw_glasses(self, c):
        s = self.s
        if not s.glasses:
            return
        for side in (-1, 1):
            ex = CX + side * EYE_DX
            c.stroke([(ex - 6.6, EYE_Y - 2.6), (ex + 6.6, EYE_Y - 2.8), (ex + 6.0, EYE_Y + 3.4), (ex - 6.0, EYE_Y + 3.2), (ex - 6.6, EYE_Y - 2.6)], 0.9, s.glasses_color, 0.85, 0.8)
            c.stroke([(ex - 5.4, EYE_Y - 1.6), (ex + 5.2, EYE_Y - 1.8)], 0.8, (240, 236, 220), 0.35, 0.8)
        c.stroke([(CX - 5.0, EYE_Y - 2.4), (CX + 5.0, EYE_Y - 2.6)], 0.9, s.glasses_color, 0.8, 0.8)

    def _draw_brows(self, c, expr):
        s = self.s
        e = EXPRESSIONS[expr]
        lift_l, lift_r = e["brow"]
        tilt = e["brow_tilt"]
        th = s.brow_thick
        for side in (-1, 1):
            ex = CX + side * EYE_DX
            lift = lift_l if side < 0 else lift_r
            inner_x = CX + side * 4.6
            outer_x = CX + side * 20.4
            inner_y = BROW_Y + 1.2 - lift + tilt * 0.9
            mid_x = (inner_x + outer_x) / 2 + side * 1.0
            mid_y = BROW_Y - 1.8 - lift - abs(tilt) * 0.5
            outer_y = BROW_Y + 1.0 - lift * 0.7 - tilt * 0.6
            pts = [
                (inner_x, inner_y + 0.6),
                (mid_x, mid_y),
                (outer_x, outer_y),
            ]
            c.stroke(pts, [th * 0.7, th, th * 0.55], s.hair_shadow, 0.95, feather=0.9)
            c.stroke([(p[0], p[1] - 0.8) for p in pts], 0.7, s.hair_light, 0.18, 0.8)
            c.stroke([(inner_x, inner_y + 1.5), (mid_x, mid_y + 1.6)], 0.8, s.skin_deep, 0.18, 1.0)

    def _restore_from_base(self, c, poly, extra=0.6):
        bb = (min(p[0] for p in poly) - 1, min(p[1] for p in poly) - 1,
              max(p[0] for p in poly) + 1, max(p[1] for p in poly) + 1)
        base = self.base
        for y in range(max(0, int(bb[1])), min(H, int(bb[3]) + 1)):
            for x in range(max(0, int(bb[0])), min(W, int(bb[2]) + 1)):
                if sd_polygon(x + 0.5, y + 0.5, poly) < extra:
                    col = base.get(x, y)
                    if col[3] > 0.5:
                        c.set(x, y, col)

    def _draw_eye(self, c, expr, side, openness, gaze, blink):
        s = self.s
        e = EXPRESSIONS[expr]
        cx = CX + side * EYE_DX
        cy = EYE_Y
        ew = 7.0
        open_amt = clamp(1.0 - blink, 0.0, 1.0) * clamp(openness, 0.0, 1.0)
        eh = 0.6 + 2.7 * open_amt
        n = 26
        top = []
        bot = []
        for i in range(n + 1):
            t = i / n
            ang = math.pi * t
            x = cx - ew + 2.0 * ew * t
            top.append((x, cy - math.sin(ang) * eh))
            bot.append((x, cy + math.sin(ang) * eh * 0.70))
        upper_lid = [(x, y) for (x, y) in top]
        closed = blink > 0.55 or openness <= 0.05

        if not closed:
            c.polygon(top + list(reversed(bot)), P.EYE_WHITE, 0.97, feather=0.65)
            c.stroke([(cx + side * 2.0, cy - eh * 0.2), (cx - side * 4.0, cy - eh * 0.35)], 1.6,
                     P.mix(P.EYE_WHITE, (110, 88, 82), 0.55), 0.30, 1.0)
            gx = clamp(gaze[0], -1.0, 1.0) * 1.6
            gy = clamp(gaze[1], -1.0, 1.0) * 1.1
            ir = 2.5
            ix = cx + gx
            iy = cy - 0.3 + gy
            c.ellipse(ix, iy, ir, ir, s.eye_color_ring, 1.0, feather=0.7)
            c.ellipse(ix, iy + 0.1, ir * 0.86, ir * 0.86, s.iris, 1.0, feather=0.7)
            c.ellipse(ix - 0.3, iy + 0.8, ir * 0.60, ir * 0.46, P.mix(s.iris, (120, 80, 30), 0.30), 0.55, feather=0.8)
            c.ellipse(ix, iy, ir * 0.44, ir * 0.50, (9, 7, 9), 1.0, feather=0.6)
            c.ellipse(ix - 0.9, iy - 1.0, 0.85, 0.75, (244, 240, 232), 0.95, feather=0.6)
            c.ellipse(ix + 0.9, iy + 1.1, 0.5, 0.4, (200, 180, 160), 0.32, feather=0.6)
            if e.get("glint"):
                c.ellipse(ix + 0.3, iy + 0.1, 0.6, 0.6, (196, 62, 50), 0.65, feather=0.6)

        lid_poly = [(cx - ew - 2.0, cy - 9.0), (cx + ew + 2.0, cy - 9.0)] + list(reversed(upper_lid))
        self._restore_from_base(c, lid_poly, 0.3)
        lash = [(x, y - 0.35) for (x, y) in upper_lid]
        c.stroke(lash, 1.15, s.hair_shadow, 0.95, feather=0.6)
        c.stroke([(cx + side * (ew - 0.5), upper_lid[-1][1] - 0.6), (cx + side * (ew + 1.4), upper_lid[-1][1] - 1.9)],
                 0.9, s.hair_shadow, 0.75, feather=0.6)
        c.stroke([(x, y + 0.55) for (x, y) in upper_lid], 0.7, s.skin_light, 0.22, 1.0)
        crease = [(x, y - 2.2 - 0.5 * s.eyes_hooded) for (x, y) in upper_lid]
        c.stroke(crease, 0.85, s.skin_deep, 0.26, 1.2)
        lower = [(x, y + eh * 0.08) for (x, y) in bot]
        c.stroke(lower, 0.8, s.skin_deep, 0.40, 0.9)
        c.stroke([(x, y + 0.9) for (x, y) in bot], 0.7, s.skin_light, 0.16, 1.0)
        c.stroke([(cx - side * 0.4, cy + eh * 0.95), (cx + side * 2.4, cy + eh * 0.92)], 0.9, s.skin_deep, 0.14, 1.3)

    def _draw_mouth(self, c, expr, open_amt=0.0, phase=0):
        s = self.s
        e = EXPRESSIONS[expr]
        mtype = e["mouth"]
        smile = e["smile"]
        cy = MOUTH_Y
        w = 11.4 * (1.0 + 0.04 * s.lip_full)
        lf = s.lip_full
        if mtype == "smile":
            smile = max(smile, 0.5)
        if mtype == "smirk":
            smile = 0.7
        corner_y = cy + 0.2 - smile * 2.3
        upper_peaks = [(CX - w * 0.30, cy - 2.4 - smile * 0.2), (CX - w * 0.10, cy - 1.5), (CX, cy - 1.9), (CX + w * 0.10, cy - 1.5), (CX + w * 0.30, cy - 2.4 - smile * 0.2)]
        open_h = 0.0
        if mtype in ("talk", "open"):
            open_h = (2.2 + 1.6 * open_amt) * (0.75 + 0.25 * phase)
        elif mtype == "parted":
            open_h = 1.6
        elif mtype in ("teeth", "grin"):
            open_h = 3.4
        lip_line = cy + 0.3 + open_h * 0.35
        upper = [(CX - w * 0.5, corner_y - 0.1)]
        upper += upper_peaks
        upper.append((CX + w * 0.5, corner_y - 0.1))
        upper += [(CX + w * 0.42, lip_line - 0.4), (CX + w * 0.2, lip_line), (CX, lip_line + 0.2), (CX - w * 0.2, lip_line), (CX - w * 0.42, lip_line - 0.4)]
        c.polygon(upper, s.lip_dark, 1.0, feather=0.75)
        c.polygon([(CX - w * 0.46, lip_line - 0.9), (CX - w * 0.2, lip_line - 0.6), (CX, lip_line - 0.3), (CX + w * 0.2, lip_line - 0.6), (CX + w * 0.46, lip_line - 0.9), (CX + w * 0.4, lip_line + 0.5), (CX - w * 0.4, lip_line + 0.5)], s.lip_base, 0.95, feather=0.7)
        lower_top = lip_line + 0.2
        lower_bot = cy + 2.6 + open_h * 1.25 + 0.5 * lf
        c.polygon([(CX - w * 0.46, lower_top), (CX - w * 0.2, lower_top + 0.4), (CX, lower_top + 0.5), (CX + w * 0.2, lower_top + 0.4), (CX + w * 0.46, lower_top), (CX + w * 0.30, lower_bot - 0.5), (CX, lower_bot), (CX - w * 0.30, lower_bot - 0.5)], s.lip_base, 1.0, feather=0.75)
        c.polygon([(CX - w * 0.30, lower_top + 1.0), (CX, lower_top + 1.4), (CX + w * 0.30, lower_top + 1.0), (CX + w * 0.16, lower_bot - 0.9), (CX - w * 0.16, lower_bot - 0.9)], s.lip_light, 0.45, feather=0.9)
        if open_h > 1.2:
            cav_h = open_h * 0.95
            c.polygon([(CX - w * 0.34, lip_line), (CX + w * 0.34, lip_line), (CX + w * 0.24, lip_line + cav_h), (CX - w * 0.24, lip_line + cav_h)], (40, 16, 18), 1.0, feather=0.7)
            if mtype in ("teeth", "grin", "talk", "open"):
                tw = w * 0.30
                c.polygon([(CX - tw, lip_line + 0.15), (CX + tw, lip_line + 0.15), (CX + tw * 0.86, lip_line + 1.15), (CX - tw * 0.86, lip_line + 1.15)], (214, 204, 188), 0.95, feather=0.6)
                if mtype in ("talk", "open"):
                    for i in range(3):
                        tx = CX - tw * 0.6 + i * tw * 0.6
                        c.stroke([(tx, lip_line + 0.2), (tx, lip_line + 1.05)], 0.4, (160, 148, 132), 0.5, 0.5)
            elif open_h < 2.5:
                c.polygon([(CX - w * 0.18, lip_line + 0.2), (CX + w * 0.18, lip_line + 0.2), (CX + w * 0.1, lip_line + 0.9), (CX - w * 0.1, lip_line + 0.9)], (206, 196, 180), 0.75, feather=0.6)
        c.stroke([(CX - w * 0.5, corner_y), (CX - w * 0.25, lip_line + 0.1), (CX, lip_line + 0.35), (CX + w * 0.25, lip_line + 0.1), (CX + w * 0.5, corner_y)], 0.9, (62, 28, 30), 0.9, feather=0.6)
        c.stroke([(CX - w * 0.5 - 1.2, corner_y - 0.2), (CX - w * 0.5, corner_y + 0.2)], 0.8, s.skin_deep, 0.35, 0.7)
        c.stroke([(CX + w * 0.5, corner_y + 0.2), (CX + w * 0.5 + 1.2, corner_y - 0.2)], 0.8, s.skin_deep, 0.35, 0.7)
        c.stroke([(CX - w * 0.18, cy - 4.6), (CX - w * 0.16, cy - 3.2)], 0.7, s.skin_deep, 0.18, 0.9)
        c.stroke([(CX + w * 0.18, cy - 4.6), (CX + w * 0.16, cy - 3.2)], 0.7, s.skin_deep, 0.18, 0.9)
        c.ellipse(CX, lower_bot + 1.4, w * 0.30, 1.5, s.skin_deep, 0.18, 1.5)
        c.ellipse(CX, lower_bot + 3.0, w * 0.20, 1.0, s.skin_light, 0.12, 1.4)

    def _draw_blood(self, c, seed=3):
        rng = random.Random(seed)
        for i in range(26):
            x = rng.uniform(38, 86)
            y = rng.uniform(30, 60)
            if math.hypot((x - CX) / 22.0, (y - (EYE_Y + 6)) / 20.0) > 1.0:
                continue
            r = rng.choice((0.4, 0.5, 0.7, 1.0, 1.4))
            c.ellipse(x, y, r, r * rng.uniform(0.6, 1.3), (128, 18, 22), rng.uniform(0.5, 0.95), 0.6)
        c.stroke([(46, 34), (47, 40), (45.5, 45)], 1.1, (120, 16, 20), 0.75, 0.8)
        c.ellipse(46.5, 46.0, 1.6, 2.2, (120, 16, 20), 0.8, 0.7)

    def frame(self, expr="neutral", gaze=None, blink=0.0, mouth=0.0, phase=0, seed=0):
        e = EXPRESSIONS[expr]
        if gaze is None:
            gaze = e["gaze"]
        key = (expr, gaze, round(blink, 1), round(mouth, 1), phase, seed)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        c = self.base.copy()
        self._draw_mouth(c, expr, mouth, phase)
        for side in (-1, 1):
            openness = e["eye_open"] * (1.0 - blink)
            self._draw_eye(c, expr, side, e["eye_open"], gaze, blink)
        self._draw_brows(c, expr)
        if e.get("blood"):
            self._draw_blood(c)
        if e.get("tint"):
            t = e["tint"]
            if t > 0:
                c.tint((220, 160, 110), t * 0.35)
            else:
                c.tint((60, 90, 120), -t * 0.45)
        if len(self._cache) > 48:
            self._cache.clear()
        self._cache[key] = c
        return c


def make_style(name):
    if name == "hannibal":
        return FaceStyle(
            name="hannibal",
            head_w=45.0,
            head_h=52.0,
            jaw=1.16,
            lip_full=1.0,
            brow_thick=2.5,
            age=1.0,
            hair_style="slick",
            hair_base=(46, 34, 28),
            hair_light=(98, 72, 52),
            hair_shadow=(24, 18, 16),
            iris=P.IRIS_AMBER,
            eye_color_ring=(38, 22, 12),
            eyes_hooded=0.7,
            skin_base=(206, 164, 138),
            skin_light=(232, 198, 172),
            skin_shadow=(146, 102, 82),
            skin_deep=(92, 62, 52),
            suit=(14, 14, 17),
            suit_light=(44, 44, 52),
            tie=(52, 14, 20),
            glasses=False,
        )
    if name == "rurke":
        return FaceStyle(
            name="rurke",
            head_w=48.0,
            head_h=52.0,
            jaw=1.05,
            brow_thick=3.0,
            age=1.35,
            hair_style="short",
            hair_base=(70, 68, 70),
            hair_light=(130, 126, 124),
            hair_shadow=(40, 38, 40),
            iris=(70, 56, 36),
            skin_base=(112, 76, 58),
            skin_light=(146, 106, 84),
            skin_shadow=(72, 46, 36),
            skin_deep=(44, 26, 22),
            lip_base=(120, 68, 62),
            lip_light=(150, 92, 82),
            lip_dark=(92, 48, 44),
            mustache=1.0,
            beard=0.5,
            suit=(26, 24, 26),
            suit_light=(58, 54, 56),
            tie=(38, 42, 58),
        )
    if name == "chilton":
        return FaceStyle(
            name="chilton",
            head_w=43.0,
            head_h=53.0,
            jaw=0.92,
            brow_thick=2.0,
            age=0.85,
            hair_style="bald_top",
            hair_base=(120, 96, 66),
            hair_light=(168, 140, 100),
            hair_shadow=(78, 58, 40),
            iris=(88, 96, 90),
            skin_base=(214, 176, 152),
            skin_light=(238, 208, 186),
            skin_shadow=(164, 118, 96),
            skin_deep=(108, 72, 58),
            glasses=True,
            glasses_color=(176, 150, 96),
            suit=(44, 34, 36),
            suit_light=(84, 66, 66),
            tie=(60, 40, 24),
            lip_full=0.8,
        )
    if name == "composer":
        return FaceStyle(
            name="composer",
            head_w=46.0,
            head_h=53.0,
            jaw=1.2,
            brow_thick=2.2,
            age=0.7,
            hair_style="short",
            hair_base=(30, 28, 30),
            hair_light=(70, 66, 68),
            hair_shadow=(16, 15, 17),
            iris=(120, 120, 124),
            skin_base=(150, 136, 128),
            skin_light=(184, 170, 158),
            skin_shadow=(96, 82, 78),
            skin_deep=(58, 48, 46),
            lip_base=(120, 86, 82),
            lip_light=(150, 112, 104),
            lip_dark=(86, 56, 54),
            suit=(18, 18, 20),
            suit_light=(40, 40, 44),
            tie=(30, 30, 34),
            beard=0.4,
            scars=((42, 24, 36, 22, (110, 40, 40), 0.5),),
        )
    if name == "heroine":
        return FaceStyle(
            name="heroine",
            head_w=41.0,
            head_h=50.0,
            jaw=0.86,
            brow_thick=1.7,
            age=0.45,
            hair_style="long",
            hair_base=(44, 30, 26),
            hair_light=(96, 66, 48),
            hair_shadow=(22, 16, 14),
            iris=P.IRIS_GREEN,
            skin_base=(216, 178, 154),
            skin_light=(242, 210, 188),
            skin_shadow=(162, 118, 100),
            skin_deep=(106, 72, 62),
            lip_base=(178, 106, 98),
            lip_light=(210, 134, 122),
            lip_dark=(138, 76, 72),
            lip_full=1.25,
            suit=(32, 34, 40),
            suit_light=(64, 68, 78),
            tie=(70, 24, 28),
            eyes_hooded=0.3,
            beard=0.0,
        )
    raise KeyError(name)


_REGISTRY = {}


def get_portrait(name):
    if name not in _REGISTRY:
        _REGISTRY[name] = Portrait(make_style(name))
    return _REGISTRY[name]
