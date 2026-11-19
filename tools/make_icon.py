import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from art.canvas import Canvas
from art import palette as P

SIZE = 256


def build():
    c = Canvas(SIZE, SIZE, (8, 7, 9, 1))
    c.radial(70, 50, 220, (96, 62, 32), 0.5, 2.0)
    c.radial(190, 70, 140, (40, 48, 62), 0.35, 2.2)
    c.vignette(0.75, 1.6)
    font = {
        "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    }
    glyph = font["H"]
    scale = 24
    gw = 5 * scale
    gh = 7 * scale
    x0 = (SIZE - gw) // 2
    y0 = (SIZE - gh) // 2 - 10
    for gy, row in enumerate(glyph):
        for gx, bit in enumerate(row):
            if bit != "1":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    px = x0 + gx * scale + dx
                    py = y0 + gy * scale + dy
                    k = 0.75 + 0.25 * math_sin((gx * 7 + gy * 3) / 9.0)
                    col = (198 * k, 168 * k, 112 * k, 1.0)
                    c.set(px, py, col)
    for x in range(x0, x0 + gw):
        c.set(x, y0 + gh + 12, (150, 36, 34, 1.0))
    c.ellipse(SIZE / 2, SIZE / 2, SIZE * 0.46, SIZE * 0.46, (0, 0, 0), 0.0, 1.0)
    return c


def math_sin(v):
    import math
    return (math.sin(v) + 1.0) / 2.0


def write_png(c, path):
    c.save_png(path, scale=1, levels=0, opaque=True)


def write_ico(png_path, ico_path):
    with open(png_path, "rb") as f:
        png = f.read()
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
    with open(ico_path, "wb") as f:
        f.write(header + entry + png)


def main():
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    c = build()
    png = os.path.join(assets, "icon.png")
    ico = os.path.join(assets, "hannibal.ico")
    write_png(c, png)
    write_ico(png, ico)
    print("icon:", ico, os.path.getsize(ico), "bytes")


if __name__ == "__main__":
    main()
