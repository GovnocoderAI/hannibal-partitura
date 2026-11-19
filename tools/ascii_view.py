import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from art.faces import get_portrait, W, H

CHARS = " .:-=+*#%@"


def ascii_view(img, x0=0, y0=0, x1=120, y1=80, sx=2, sy=2):
    out = []
    for y in range(y0, y1, sy):
        line = []
        for x in range(x0, x1, sx):
            r = g = b = 0.0
            n = 0
            for dy in range(sy):
                for dx in range(sx):
                    c = img.get(x + dx, y + dy)
                    if c[3] > 0.3:
                        r += c[0]
                        g += c[1]
                        b += c[2]
                        n += 1
            if not n:
                line.append(" ")
                continue
            lum = (0.30 * r + 0.59 * g + 0.11 * b) / (n * 255.0)
            if lum < 0.03:
                line.append(" ")
            else:
                line.append(CHARS[min(len(CHARS) - 1, int(lum * len(CHARS)))])
        out.append("".join(line))
    return "\n".join(out)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "hannibal"
    expr = sys.argv[2] if len(sys.argv) > 2 else "neutral"
    p = get_portrait(name)
    img = p.frame(expr)
    print(ascii_view(img, 30, 0, 90, 66, 1, 1))
