import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from art.faces import get_portrait, W, H


def bbox(img):
    pts = [(x, y) for y in range(H) for x in range(W) if img.get(x, y)[3] > 0.5]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return len(pts), (min(xs), min(ys), max(xs), max(ys))


def avg(img, x0, y0, x1, y1):
    r = g = b = 0
    n = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = img.get(x, y)
            if c[3] > 0.5:
                r += c[0]
                g += c[1]
                b += c[2]
                n += 1
    if not n:
        return None
    return (round(r / n), round(g / n), round(b / n), n)


p = get_portrait("hannibal")
b = p.base
print("opaque", bbox(b))
for expr in ("neutral", "predatory", "intimate", "closed"):
    f = p.frame(expr)
    diff = sum(1 for y in range(H) for x in range(W) if abs(f.get(x, y)[0] - b.get(x, y)[0]) > 2)
    print(expr, "changed", diff)
print("forehead", avg(b, 50, 12, 70, 20))
print("cheek", avg(b, 42, 32, 50, 42))
print("eye", avg(p.frame("neutral"), 43, 24, 54, 30))
print("lips", avg(p.frame("neutral"), 54, 42, 66, 49))
print("suit", avg(b, 10, 70, 40, 79))
print("hair", avg(b, 50, 2, 70, 8))
print("neck", avg(b, 55, 58, 65, 62))
for name in ("rurke", "chilton", "composer", "heroine"):
    q = get_portrait(name)
    print(name, bbox(q.base))
