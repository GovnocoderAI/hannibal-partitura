import math
import struct
import zlib
from array import array


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


BAYER = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


class Canvas:
    __slots__ = ("w", "h", "px")

    def __init__(self, w, h, color=(0, 0, 0, 0)):
        self.w = w
        self.h = h
        r, g, b, a = color
        self.px = array("f", [r, g, b, a]) * (w * h)

    def copy(self):
        c = Canvas(self.w, self.h)
        c.px = array("f", self.px)
        return c

    def get(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return (0, 0, 0, 0)
        i = (y * self.w + x) * 4
        p = self.px
        return (p[i], p[i + 1], p[i + 2], p[i + 3])

    def set(self, x, y, color):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 4
        p = self.px
        p[i] = color[0]
        p[i + 1] = color[1]
        p[i + 2] = color[2]
        p[i + 3] = color[3] if len(color) > 3 else 1.0

    def blend(self, x, y, color, alpha=1.0):
        if alpha <= 0.001:
            return
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        p = self.px
        i = (y * self.w + x) * 4
        sa = alpha if len(color) < 4 else alpha * color[3]
        if sa <= 0.001:
            return
        da = p[i + 3]
        if sa >= 1.0:
            p[i] = color[0]
            p[i + 1] = color[1]
            p[i + 2] = color[2]
            p[i + 3] = 1.0
            return
        na = sa + da * (1.0 - sa)
        if na <= 0.0001:
            return
        p[i] = (color[0] * sa + p[i] * da * (1.0 - sa)) / na
        p[i + 1] = (color[1] * sa + p[i + 1] * da * (1.0 - sa)) / na
        p[i + 2] = (color[2] * sa + p[i + 2] * da * (1.0 - sa)) / na
        p[i + 3] = na

    def fill(self, color):
        r, g, b = color[0], color[1], color[2]
        a = color[3] if len(color) > 3 else 1.0
        self.px = array("f", [r, g, b, a]) * (self.w * self.h)

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        for y in range(max(0, int(y0)), min(self.h, int(y1) + 1)):
            for x in range(max(0, int(x0)), min(self.w, int(x1) + 1)):
                self.blend(x, y, color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, feather=0.9):
        if rx <= 0 or ry <= 0:
            return
        x0 = max(0, int(cx - rx - feather - 1))
        x1 = min(self.w - 1, int(cx + rx + feather + 1))
        y0 = max(0, int(cy - ry - feather - 1))
        y1 = min(self.h - 1, int(cy + ry + feather + 1))
        k = min(rx, ry)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                d = (math.hypot((x - cx) / rx, (y - cy) / ry) - 1.0) * k
                cov = clamp(0.5 - d / feather, 0.0, 1.0)
                if cov > 0.002:
                    self.blend(x, y, color, alpha * cov)

    def sdf(self, fn, color, alpha=1.0, feather=0.9, bbox=None):
        if bbox is None:
            x0, y0, x1, y1 = 0, 0, self.w - 1, self.h - 1
        else:
            x0, y0, x1, y1 = bbox
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w - 1, int(x1))
        y1 = min(self.h - 1, int(y1))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                d = fn(x + 0.5, y + 0.5)
                cov = clamp(0.5 - d / feather, 0.0, 1.0)
                if cov > 0.002:
                    self.blend(x, y, color, alpha * cov)

    def polygon(self, pts, color, alpha=1.0, feather=0.9):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bb = (min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)

        def f(x, y):
            return sd_polygon(x, y, pts)

        self.sdf(f, color, alpha, feather, bb)

    def stroke(self, pts, width, color, alpha=1.0, feather=0.9):
        if len(pts) < 2:
            return
        widths = width if isinstance(width, (list, tuple)) else [width] * len(pts)
        segs = []
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1], widths[i], widths[i + 1]))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        m = max(widths) if isinstance(width, (list, tuple)) else width
        bb = (min(xs) - m - 2, min(ys) - m - 2, max(xs) + m + 2, max(ys) + m + 2)

        def f(x, y):
            best = 1e9
            for (a, b, wa, wb) in segs:
                best = min(best, sd_segment(x, y, a, b) - wa * 0.5)
            return best

        self.sdf(f, color, alpha, feather, bb)

    def vertical_gradient(self, y0, y1, top, bottom):
        span = max(1, y1 - y0)
        for y in range(int(y0), int(y1)):
            if y < 0 or y >= self.h:
                continue
            t = (y - y0) / span
            r = top[0] + (bottom[0] - top[0]) * t
            g = top[1] + (bottom[1] - top[1]) * t
            b = top[2] + (bottom[2] - top[2]) * t
            for x in range(self.w):
                i = (y * self.w + x) * 4
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b
                self.px[i + 3] = 1.0

    def radial(self, cx, cy, radius, color, alpha=1.0, power=1.0):
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot(x - cx, y - cy) / max(1.0, radius)
                if d >= 1.0:
                    continue
                k = (1.0 - d) ** power
                self.blend(x, y, color, alpha * k)

    def vignette(self, strength=0.55, power=1.9, color=(0, 0, 0)):
        cx = self.w / 2.0
        cy = self.h / 2.0
        m = math.hypot(cx, cy)
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot(x - cx, y - cy) / m
                k = strength * (d ** power)
                self.blend(x, y, color, clamp(k, 0.0, 1.0))

    def grain(self, amount=0.045, seed=7, dark_only=False):
        import random

        rng = random.Random(seed)
        p = self.px
        n = self.w * self.h
        for i in range(n):
            j = i * 4
            if p[j + 3] <= 0.02:
                continue
            g = (rng.random() - 0.5) * 2.0 * amount * 255.0
            if dark_only and g > 0:
                continue
            p[j] = clamp(p[j] + g, 0.0, 255.0)
            p[j + 1] = clamp(p[j + 1] + g, 0.0, 255.0)
            p[j + 2] = clamp(p[j + 2] + g, 0.0, 255.0)

    def blur(self, radius=2):
        r = int(radius)
        if r < 1:
            return
        w, h = self.w, self.h
        src = self.px
        tmp = array("f", src)
        for y in range(h):
            row = y * w
            for x in range(w):
                i = (row + x) * 4
                ar = ag = ab = aa = 0.0
                cnt = 0
                for dx in range(-r, r + 1):
                    xx = x + dx
                    if 0 <= xx < w:
                        j = (row + xx) * 4
                        ar += src[j]
                        ag += src[j + 1]
                        ab += src[j + 2]
                        aa += src[j + 3]
                        cnt += 1
                j = i
                tmp[j] = ar / cnt
                tmp[j + 1] = ag / cnt
                tmp[j + 2] = ab / cnt
                tmp[j + 3] = aa / cnt
        out = array("f", tmp)
        for y in range(h):
            for x in range(w):
                i = (y * w + x) * 4
                ar = ag = ab = aa = 0.0
                cnt = 0
                for dy in range(-r, r + 1):
                    yy = y + dy
                    if 0 <= yy < h:
                        j = (yy * w + x) * 4
                        ar += tmp[j]
                        ag += tmp[j + 1]
                        ab += tmp[j + 2]
                        aa += tmp[j + 3]
                        cnt += 1
                out[i] = ar / cnt
                out[i + 1] = ag / cnt
                out[i + 2] = ab / cnt
                out[i + 3] = aa / cnt
        self.px = out

    def composite(self, src, dx=0, dy=0, alpha=1.0):
        p = self.px
        q = src.px
        for y in range(src.h):
            ty = y + dy
            if ty < 0 or ty >= self.h:
                continue
            for x in range(src.w):
                tx = x + dx
                if tx < 0 or tx >= self.w:
                    continue
                j = (y * src.w + x) * 4
                sa = q[j + 3] * alpha
                if sa <= 0.003:
                    continue
                i = (ty * self.w + tx) * 4
                da = p[i + 3]
                na = sa + da * (1.0 - sa)
                if na <= 0.0001:
                    continue
                p[i] = (q[j] * sa + p[i] * da * (1.0 - sa)) / na
                p[i + 1] = (q[j + 1] * sa + p[i + 1] * da * (1.0 - sa)) / na
                p[i + 2] = (q[j + 2] * sa + p[i + 2] * da * (1.0 - sa)) / na
                p[i + 3] = na

    def multiply_alpha(self, mask_fn, strength):
        p = self.px
        for y in range(self.h):
            for x in range(self.w):
                i = (y * self.w + x) * 4
                if p[i + 3] > 0.01:
                    p[i + 3] *= 1.0 - clamp(mask_fn(x, y) * strength, 0.0, 1.0)

    def tint(self, color, amount, bbox=None):
        x0, y0, x1, y1 = bbox if bbox else (0, 0, self.w - 1, self.h - 1)
        p = self.px
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                i = (y * self.w + x) * 4
                if p[i + 3] < 0.05:
                    continue
                self.blend(x, y, color, amount)

    def crop(self, x0, y0, w, h):
        c = Canvas(w, h)
        for y in range(h):
            for x in range(w):
                c.set(x, y, self.get(x0 + x, y0 + y))
        return c

    def to_png_bytes(self, scale=1, levels=0, dither=0.85, opaque=True):
        w = self.w * scale
        h = self.h * scale
        rows = bytearray()
        p = self.px
        for y in range(h):
            rows.append(0)
            sy = y // scale
            for x in range(w):
                sx = x // scale
                i = (sy * self.w + sx) * 4
                r, g, b, a = p[i], p[i + 1], p[i + 2], p[i + 3]
                if levels > 1:
                    t = (BAYER[y % 4][x % 4] / 16.0 - 0.5) * (255.0 / (levels - 1)) * dither
                    r = clamp(r + t, 0, 255)
                    g = clamp(g + t, 0, 255)
                    b = clamp(b + t, 0, 255)
                if opaque:
                    if a < 0.5:
                        r = g = b = 0
                    rows += bytes((int(r), int(g), int(b), 255))
                else:
                    rows += bytes((int(r), int(g), int(b), int(a * 255)))
        color_type = 6 if not opaque else 6
        raw = bytes(rows)
        comp = zlib.compress(raw, 9)

        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return c

        ihdr = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp)
            + chunk(b"IEND", b"")
        )

    def save_png(self, path, scale=1, levels=0, dither=0.85, opaque=True):
        data = self.to_png_bytes(scale, levels, dither, opaque)
        with open(path, "wb") as f:
            f.write(data)


def sd_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    L = vx * vx + vy * vy
    if L < 1e-9:
        return math.hypot(wx, wy)
    t = clamp((wx * vx + wy * vy) / L, 0.0, 1.0)
    return math.hypot(wx - vx * t, wy - vy * t)


def sd_polygon(px, py, pts):
    n = len(pts)
    inside = False
    d = 1e9
    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        d = min(d, sd_segment(px, py, a, b))
        if (a[1] > py) != (b[1] > py):
            xin = (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]
            if px < xin:
                inside = not inside
    return -d if inside else d


def sd_ellipse(px, py, cx, cy, rx, ry):
    return (math.hypot((px - cx) / rx, (py - cy) / ry) - 1.0) * min(rx, ry)


def sd_ellipse_raw(px, py, cx, cy, rx, ry):
    return math.hypot((px - cx) / rx, (py - cy) / ry)


def lerp_color(c1, c2, t):
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


mix_color = lerp_color
