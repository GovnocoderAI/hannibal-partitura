import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from art.canvas import Canvas
from art.faces import get_portrait, EXPRESSIONS, W, H
from art.scenes_art import get_bg
from engine.term import Screen, rgb


class TestCanvas(unittest.TestCase):
    def test_png(self):
        c = Canvas(8, 8)
        c.ellipse(4, 4, 3, 3, (200, 100, 50), 1.0)
        data = c.to_png_bytes(scale=2, levels=16)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_composite(self):
        a = Canvas(4, 4, (0, 0, 0, 1))
        b = Canvas(4, 4, (255, 128, 64, 1))
        a.composite(b)
        r, g, bl, al = a.get(1, 1)
        self.assertAlmostEqual(r, 255, delta=1)
        self.assertAlmostEqual(g, 128, delta=1)

    def test_blur(self):
        c = Canvas(6, 6)
        c.set(2, 2, (255, 255, 255, 1))
        c.blur(1)
        self.assertGreater(c.get(3, 2)[0], 0)


class TestPortraits(unittest.TestCase):
    def test_expressions(self):
        p = get_portrait("hannibal")
        base = p.frame("neutral")
        warm = p.frame("warm")
        diff = 0
        for y in range(H):
            for x in range(W):
                if abs(base.get(x, y)[0] - warm.get(x, y)[0]) > 3:
                    diff += 1
        self.assertGreater(diff, 100)

    def test_alpha(self):
        p = get_portrait("hannibal")
        pts = [(x, y) for y in range(H) for x in range(W) if p.base.get(x, y)[3] > 0.5]
        self.assertGreater(len(pts), 2500)
        xs = [x for x, y in pts]
        self.assertLess(min(xs), 40)
        self.assertGreater(max(xs), 80)

    def test_all_styles(self):
        for name in ("hannibal", "rurke", "chilton", "composer", "heroine"):
            p = get_portrait(name)
            self.assertIsNotNone(p.base)

    def test_bg(self):
        for name in ("cell", "office", "dinner", "snow", "house", "title"):
            c = get_bg(name)
            self.assertEqual(c.w, 120)
            self.assertEqual(c.h, 80)
            self.assertGreater(c.get(60, 40)[3], 0.5)


class TestScreen(unittest.TestCase):
    class Dummy:
        def __init__(self):
            self.data = []

        def write(self, s):
            self.data.append(s)

    def test_present(self):
        s = Screen(60, 20)
        c = Canvas(60, 40)
        c.vertical_gradient(0, 40, (10, 10, 20), (50, 30, 20))
        s.art(c)
        s.text(2, 18, "тест", rgb(200, 180, 140))
        out = self.Dummy()
        s.present(out)
        joined = "".join(out.data)
        self.assertIn("▀", joined)
        self.assertIn("38;2;", joined)
        self.assertIn("тест", joined)


if __name__ == "__main__":
    unittest.main()
