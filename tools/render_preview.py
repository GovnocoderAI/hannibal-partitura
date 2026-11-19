import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from art.canvas import Canvas
from art import palette as P
from art.faces import get_portrait, EXPRESSIONS, W, H

OUT = os.path.join(ROOT, "preview")
os.makedirs(OUT, exist_ok=True)


def backdrop():
    c = Canvas(W, H)
    c.vertical_gradient(0, H, (16, 14, 16), (8, 7, 9))
    c.radial(34, 22, 58, (70, 46, 26), 0.28, 2.0)
    c.radial(92, 30, 44, (40, 46, 62), 0.16, 2.2)
    c.grain(0.02, 3)
    return c


def portrait_on_bg(p, expr, blink=0.0, mouth=0.0, phase=0):
    bg = backdrop()
    bg.composite(p.frame(expr, blink=blink, mouth=mouth, phase=phase))
    bg.vignette(0.35, 2.0)
    return bg


def sheet(names, out_name, scale=2):
    cols = 3
    rows = (len(names) + cols - 1) // cols
    sheet = Canvas(W * cols, H * rows)
    for i, (name, expr) in enumerate(names):
        p = get_portrait(name)
        img = portrait_on_bg(p, expr)
        sheet.composite(img, (i % cols) * W, (i // cols) * H)
    sheet.save_png(os.path.join(OUT, out_name), scale=scale, levels=20, dither=0.6)
    print("wrote", out_name)


def main():
    names = [(n, e) for (n, e) in [
        ("hannibal", "neutral"), ("hannibal", "warm"), ("hannibal", "amused"),
        ("hannibal", "predatory"), ("hannibal", "cold"), ("hannibal", "intimate"),
        ("hannibal", "closed"), ("hannibal", "hungry"), ("hannibal", "bloody"),
        ("hannibal", "smile_talk"), ("hannibal", "pain"), ("hannibal", "neutral"),
    ]]
    sheet(names, "hannibal_expressions.png", 2)

    for expr in ("neutral", "predatory", "warm", "intimate"):
        p = get_portrait("hannibal")
        img = portrait_on_bg(p, expr)
        img.save_png(os.path.join(OUT, f"hannibal_{expr}.png"), scale=4, levels=24, dither=0.6)
        crop = img.crop(28, 0, 64, 64)
        crop.save_png(os.path.join(OUT, f"hannibal_{expr}_face.png"), scale=7, levels=24, dither=0.5)

    others = [("rurke", "neutral"), ("chilton", "neutral"), ("composer", "neutral"),
              ("heroine", "neutral"), ("hannibal", "neutral"), ("rurke", "cold")]
    sheet(others, "cast.png", 2)
    print("done")


if __name__ == "__main__":
    main()
