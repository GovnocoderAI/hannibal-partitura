import ctypes
import msvcrt
import os
import shutil
import sys
import time

STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
ENABLE_PROCESSED_OUTPUT = 0x0001

BLACK = 0x000000
CLEAR_SEQ = "\x1b[0m"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
ALT_ON = "\x1b[?1049h"
ALT_OFF = "\x1b[?1049l"
SYNC_ON = "\x1b[?2026h"
SYNC_OFF = "\x1b[?2026l"

_fg_cache = {}


def rgb(r, g, b):
    r = 0 if r < 0 else 255 if r > 255 else int(r)
    g = 0 if g < 0 else 255 if g > 255 else int(g)
    b = 0 if b < 0 else 255 if b > 255 else int(b)
    return (r << 16) | (g << 8) | b


def unpack(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def mix_int(c1, c2, t):
    if t <= 0:
        return c1
    if t >= 1:
        return c2
    r1, g1, b1 = unpack(c1)
    r2, g2, b2 = unpack(c2)
    return rgb(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def scale_int(c, k):
    r, g, b = unpack(c)
    return rgb(r * k, g * k, b * k)


def _sgr(fg, bg):
    key = (fg, bg)
    s = _fg_cache.get(key)
    if s is None:
        r, g, b = unpack(fg)
        br, bgc, bb = unpack(bg)
        s = f"\x1b[38;2;{r};{g};{b};48;2;{br};{bgc};{bb}m"
        _fg_cache[key] = s
    return s


class Console:
    def __init__(self, title="Ганнибал. Партитура"):
        self.title = title
        self.hwnd = None
        self._old_mode = None
        self._in_alt = False

    def setup(self):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        try:
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
        try:
            k32 = ctypes.windll.kernel32
            handle = k32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_uint32()
            if k32.GetConsoleMode(handle, ctypes.byref(mode)):
                self._old_mode = mode.value
                k32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING | ENABLE_PROCESSED_OUTPUT)
        except Exception:
            pass
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(self.title)
        except Exception:
            pass
        self.write(ALT_ON)
        self._in_alt = True
        self.write(HIDE_CURSOR)
        self.clear()

    def restore(self):
        try:
            self.write(SHOW_CURSOR)
            if self._in_alt:
                self.write(ALT_OFF)
                self._in_alt = False
            k32 = ctypes.windll.kernel32
            handle = k32.GetStdHandle(STD_OUTPUT_HANDLE)
            if self._old_mode is not None:
                k32.SetConsoleMode(handle, self._old_mode)
        except Exception:
            pass

    def write(self, s):
        try:
            sys.stdout.buffer.write(s.encode("utf-8", "replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass

    def clear(self):
        self.write("\x1b[2J\x1b[H")

    def size(self):
        try:
            sz = shutil.get_terminal_size(fallback=(120, 40))
            return max(40, sz.columns), max(16, sz.lines)
        except Exception:
            return 120, 40

    def poll(self):
        events = []
        for _ in range(48):
            if not msvcrt.kbhit():
                break
            try:
                ch = msvcrt.getwch()
            except Exception:
                break
            if ch in ("\x00", "\xe0"):
                try:
                    code = msvcrt.getwch()
                except Exception:
                    continue
                mapping = {
                    "H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT",
                    "I": "PGUP", "Q": "PGDN", "G": "HOME", "O": "END",
                    "S": "DELETE",
                }
                events.append(mapping.get(code, "?"))
                continue
            if ch == "\r":
                events.append("ENTER")
            elif ch == "\n":
                events.append("ENTER")
            elif ch == "\x1b":
                seq = ""
                t0 = time.perf_counter()
                while len(seq) < 2 and time.perf_counter() - t0 < 0.02:
                    if msvcrt.kbhit():
                        seq += msvcrt.getwch()
                    else:
                        time.sleep(0.001)
                if seq.startswith("["):
                    events.append({
                        "A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT",
                        "H": "HOME", "F": "END", "5~": "PGUP", "6~": "PGDN",
                    }.get(seq, "ESC"))
                else:
                    events.append("ESC")
            elif ch == "\t":
                events.append("TAB")
            elif ch == "\x08":
                events.append("BACKSPACE")
            elif ch == "\x03":
                events.append("CTRL_C")
            elif ch == "\x00":
                continue
            elif ch == " ":
                events.append("SPACE")
            else:
                events.append(ch)
        return events


class Screen:
    __slots__ = ("cols", "rows", "cells", "prev", "dirty_all")

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [(" ", rgb(200, 200, 200), rgb(0, 0, 0))] * (cols * rows)
        self.prev = [None] * (cols * rows)
        self.dirty_all = True

    def clear(self, ch=" ", fg=rgb(200, 200, 200), bg=rgb(0, 0, 0)):
        self.cells = [(ch, fg, bg)] * (self.cols * self.rows)

    def put(self, x, y, ch, fg=None, bg=None):
        if x < 0 or y < 0 or x >= self.cols or y >= self.rows:
            return
        i = y * self.cols + x
        old = self.cells[i]
        self.cells[i] = (ch, old[1] if fg is None else fg, old[2] if bg is None else bg)

    def fill(self, x0, y0, x1, y1, ch, fg, bg):
        for y in range(max(0, y0), min(self.rows, y1 + 1)):
            base = y * self.cols
            for x in range(max(0, x0), min(self.cols, x1 + 1)):
                self.cells[base + x] = (ch, fg, bg)

    def text(self, x, y, s, fg, bg=None):
        for i, ch in enumerate(s):
            self.put(x + i, y, ch, fg, bg)

    def panel(self, x0, y0, x1, y1, tint, alpha=0.86, border=None, border_fg=None):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.cols - 1, x1)
        y1 = min(self.rows - 1, y1)
        if x1 < x0 or y1 < y0:
            return
        r, g, b = unpack(tint)
        h = max(1, y1 - y0)
        span = x1 - x0 + 1
        for y in range(y0, y1 + 1):
            k = 0.90 + 0.16 * (1.0 - (y - y0) / h)
            col = rgb(r * k, g * k, b * k)
            base = y * self.cols
            self.cells[base + x0: base + x1 + 1] = [(" ", col, col)] * span
        if border:
            bfg = border_fg if border_fg is not None else tint
            self._border(x0, y0, x1, y1, border, bfg)

    def _border(self, x0, y0, x1, y1, chars, fg):
        tl, tr, bl, br, hz, vt = chars
        for x in range(x0 + 1, x1):
            self.put(x, y0, hz, fg)
            self.put(x, y1, hz, fg)
        for y in range(y0 + 1, y1):
            self.put(x0, y, vt, fg)
            self.put(x1, y, vt, fg)
        self.put(x0, y0, tl, fg)
        self.put(x1, y0, tr, fg)
        self.put(x0, y1, bl, fg)
        self.put(x1, y1, br, fg)

    def dim_except(self, strength=0.45, tint=rgb(0, 0, 0)):
        for i, (ch, fg, bg) in enumerate(self.cells):
            self.cells[i] = (ch, mix_int(fg, tint, strength), mix_int(bg, tint, strength))

    def art(self, canvas, ox=0, oy=0, scale=1.0, region=None, ascii_mode=False):
        sw = canvas.w
        sh = canvas.h
        px = canvas.px
        sc = 1.0 / scale if scale > 0 else 1.0
        cols = self.cols
        rows = self.rows
        cells = self.cells
        if region is None:
            rx0, ry0, rx1, ry1 = 0, 0, cols - 1, rows - 1
        else:
            rx0, ry0, rx1, ry1 = region
        rx0 = max(0, int(rx0))
        ry0 = max(0, int(ry0))
        rx1 = min(cols - 1, int(rx1))
        ry1 = min(rows - 1, int(ry1))
        if rx1 < rx0 or ry1 < ry0:
            return
        xs = [int((x - ox) * sc) for x in range(rx0, rx1 + 1)]
        ytop = [int((y * 2 - oy) * sc) for y in range(ry0, ry1 + 1)]
        ybot = [int((y * 2 + 1 - oy) * sc) for y in range(ry0, ry1 + 1)]
        chars = " .:-=+*#%@"
        for yi, y in enumerate(range(ry0, ry1 + 1)):
            row = y * cols
            iy0 = ytop[yi]
            iy1 = ybot[yi]
            ok0 = 0 <= iy0 < sh
            ok1 = 0 <= iy1 < sh
            b0 = iy0 * sw if ok0 else 0
            b1 = iy1 * sw if ok1 else 0
            for xi, x in enumerate(range(rx0, rx1 + 1)):
                sx = xs[xi]
                if sx < 0 or sx >= sw:
                    continue
                fg = cells[row + x][1]
                bg = cells[row + x][2]
                if ok0:
                    i = (b0 + sx) * 4
                    a = px[i + 3]
                    if a > 0.03:
                        t = (int(px[i]) << 16) | (int(px[i + 1]) << 8) | int(px[i + 2])
                        fg = t if a >= 0.97 else mix_int(fg, t, a)
                if ok1:
                    i = (b1 + sx) * 4
                    a = px[i + 3]
                    if a > 0.03:
                        t = (int(px[i]) << 16) | (int(px[i + 1]) << 8) | int(px[i + 2])
                        bg = t if a >= 0.97 else mix_int(bg, t, a)
                if ascii_mode:
                    lum = ((fg >> 16) & 255) * 3 + ((fg >> 8) & 255) * 6 + (fg & 255)
                    k = lum // 700
                    if k > 9:
                        k = 9
                    if k < 1:
                        k = 1
                    cells[row + x] = (chars[k], fg, bg)
                else:
                    cells[row + x] = ("▀", fg, bg)

    def art_overlay(self, canvas, ox=0, oy=0, scale=1.0, region=None):
        sw = canvas.w
        sh = canvas.h
        px = canvas.px
        sc = 1.0 / scale if scale > 0 else 1.0
        cols = self.cols
        rows = self.rows
        if region is None:
            rx0, ry0, rx1, ry1 = 0, 0, cols - 1, rows - 1
        else:
            rx0, ry0, rx1, ry1 = region
        rx0 = max(0, int(rx0))
        ry0 = max(0, int(ry0))
        rx1 = min(cols - 1, int(rx1))
        ry1 = min(rows - 1, int(ry1))
        if rx1 < rx0 or ry1 < ry0:
            return []
        xs = [int((x - ox) * sc) for x in range(rx0, rx1 + 1)]
        ytop = [int((y * 2 - oy) * sc) for y in range(ry0, ry1 + 1)]
        ybot = [int((y * 2 + 1 - oy) * sc) for y in range(ry0, ry1 + 1)]
        out = []
        for yi, y in enumerate(range(ry0, ry1 + 1)):
            iy0 = ytop[yi]
            iy1 = ybot[yi]
            ok0 = 0 <= iy0 < sh
            ok1 = 0 <= iy1 < sh
            b0 = iy0 * sw if ok0 else 0
            b1 = iy1 * sw if ok1 else 0
            row = y * cols
            for xi, x in enumerate(range(rx0, rx1 + 1)):
                sx = xs[xi]
                if sx < 0 or sx >= sw:
                    continue
                fa = 0.0
                ba = 0.0
                fg = 0
                bg = 0
                if ok0:
                    i = (b0 + sx) * 4
                    fa = px[i + 3]
                    if fa > 0.03:
                        fg = (int(px[i]) << 16) | (int(px[i + 1]) << 8) | int(px[i + 2])
                if ok1:
                    i = (b1 + sx) * 4
                    ba = px[i + 3]
                    if ba > 0.03:
                        bg = (int(px[i]) << 16) | (int(px[i + 1]) << 8) | int(px[i + 2])
                if fa > 0.03 or ba > 0.03:
                    out.append((row + x, fg, fa, bg, ba))
        return out

    def apply_overlay(self, items):
        cells = self.cells
        for idx, fg, fa, bg, ba in items:
            ch, ofg, obg = cells[idx]
            nf = ofg
            nb = obg
            if fa > 0.03:
                nf = fg if fa >= 0.97 else mix_int(ofg, fg, fa)
            if ba > 0.03:
                nb = bg if ba >= 0.97 else mix_int(obg, bg, ba)
            cells[idx] = ("▀", nf, nb)

    def effects(self, brightness=1.0, tint=None, tint_amt=0.0, grain=0.0, seed=1):
        cells = self.cells
        n = len(cells)
        if brightness != 1.0:
            lut = [0] * 256
            for v in range(256):
                q = int(v * brightness)
                lut[v] = 0 if q < 0 else 255 if q > 255 else q
            for i in range(n):
                ch, fg, bg = cells[i]
                cells[i] = (
                    ch,
                    (lut[(fg >> 16) & 255] << 16) | (lut[(fg >> 8) & 255] << 8) | lut[fg & 255],
                    (lut[(bg >> 16) & 255] << 16) | (lut[(bg >> 8) & 255] << 8) | lut[bg & 255],
                )
        if tint is not None and tint_amt > 0.0:
            for i in range(n):
                ch, fg, bg = cells[i]
                cells[i] = (ch, mix_int(fg, tint, tint_amt), mix_int(bg, tint, tint_amt))
        if grain > 0.0:
            import random

            rng = random.Random(seed)
            cnt = int(n * grain * 1.6)
            for _ in range(cnt):
                i = rng.randrange(n)
                ch, fg, bg = cells[i]
                k = 0.78 + rng.random() * 0.14
                cells[i] = (ch, scale_int(fg, k), scale_int(bg, k))

    def present(self, console):
        out = [SYNC_ON]
        last_fg = -1
        last_bg = -1
        for y in range(self.rows):
            base = y * self.cols
            x = 0
            while x < self.cols:
                i = base + x
                cur = self.cells[i]
                if self.prev[i] == cur and not self.dirty_all:
                    x += 1
                    continue
                run = [cur]
                j = x + 1
                while j < self.cols:
                    k = base + j
                    if self.prev[k] == self.cells[k] and not self.dirty_all:
                        break
                    run.append(self.cells[k])
                    j += 1
                out.append(f"\x1b[{y + 1};{x + 1}H")
                last_fg = -1
                last_bg = -1
                buf = []
                for (ch, fg, bg) in run:
                    if fg != last_fg or bg != last_bg:
                        buf.append(_sgr(fg, bg))
                        last_fg = fg
                        last_bg = bg
                    buf.append(ch)
                for idx in range(j - x):
                    self.prev[base + x + idx] = run[idx]
                out.append("".join(buf))
                x = j
        out.append(CLEAR_SEQ)
        out.append(SYNC_OFF)
        console.write("".join(out))
        self.dirty_all = False
