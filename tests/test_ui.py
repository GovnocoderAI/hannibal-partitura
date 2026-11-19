import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from engine.game import Game, Layout, wrap
from engine import save as savemod

PICKS_PARTITURA = {"p_3": 1, "p_4": 0, "p_6": 0, "p_8": 0, "p_9": 0, "c1_2": 1, "c1_4": 0,
                   "c1_6": 1, "c1_7": 1, "c1_9": 2, "c2_3": 2, "c2_4": 0, "c2_6": 1,
                   "c2_7": 0, "c2_8": 0, "c2_10": 2, "c3_1": 1, "c3_3": 1, "c3_6": 1, "c3_8": 0}


def start_game(g, name="Тест"):
    g.set_mode("disclaimer")
    g.step(["ENTER"])
    g.step(["ENTER"])
    for ch in name:
        g.step([ch])
    g.step(["ENTER"])


def play(g, picks, limit=1500):
    for i in range(limit):
        if g.mode == "ending":
            return True
        if g.mode != "game" or g.runner is None:
            return False
        render = (i % 60 == 0)
        if g.runner.current_choices():
            if not g.type_finished():
                g.step([], render=render)
                continue
            if g.uipage + 1 < len(g.uipages):
                g.step(["SPACE"], render=render)
                continue
            idx = picks.get(g.runner.node_id, 0)
            choices = g.runner.current_choices()
            if idx >= len(choices) or not g.runner.choice_enabled(choices[idx]):
                idx = 0
            g.sel = idx
            if g.choice_shown_t >= 0 and g.t - g.choice_shown_t < 0.12:
                g.step([], render=render)
                continue
            g.step(["ENTER"], render=render)
        else:
            g.step(["SPACE"], render=render)
    return False


class TestUI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hannibal_ui_")
        self._save_dir = savemod.SAVE_DIR
        self._settings_path = savemod.SETTINGS_PATH
        savemod.SAVE_DIR = os.path.join(self.tmp, "saves")
        savemod.SETTINGS_PATH = os.path.join(self.tmp, "settings.json")

    def tearDown(self):
        savemod.SAVE_DIR = self._save_dir
        savemod.SETTINGS_PATH = self._settings_path

    def make(self, w=120, h=40):
        g = Game(headless=True, width=w, height=h)
        g.settings["text_speed"] = 3
        g.settings["sound"] = 0
        return g

    def test_new_game_name(self):
        g = self.make()
        start_game(g, "Аня")
        self.assertEqual(g.mode, "game")
        self.assertEqual(g.runner.name, "Аня")
        self.assertEqual(g.runner.node_id, "p_1")

    def test_full_route(self):
        g = self.make()
        start_game(g)
        self.assertTrue(play(g, PICKS_PARTITURA))
        self.assertEqual(g.runner.ending, "partitura")
        self.assertEqual(g.mode, "ending")

    def test_screens_render(self):
        g = self.make()
        for mode in ("disclaimer", "title", "name", "about"):
            g.set_mode(mode)
            g.draw()
        start_game(g)
        for mode in ("pause", "history", "saves", "settings"):
            g.set_mode(mode)
            g.prev_mode = "game"
            g.slot_mode = "save"
            g.draw()
        self.assertTrue(any(c[0] != " " for c in g.screen.cells))

    def test_compact_layout(self):
        g = self.make(100, 30)
        start_game(g)
        self.assertEqual(g.layout.text_lines, 3)
        g.draw()
        self.assertEqual(len(g.screen.cells), 100 * 30)

    def test_pagination_fits(self):
        g = self.make()
        start_game(g)
        play(g, PICKS_PARTITURA, limit=60)
        for page in g.uipages:
            for line in page:
                self.assertLessEqual(len(line), g.layout.text_w)

    def test_autosave(self):
        g = self.make()
        start_game(g)
        self.assertIsNotNone(savemod.load_game("auto"))

    def test_load_autosave(self):
        g = self.make()
        start_game(g)
        play(g, PICKS_PARTITURA, limit=40)
        data = savemod.load_game("auto")
        self.assertIsNotNone(data)
        g.load_state(data)
        self.assertEqual(g.mode, "game")
        self.assertEqual(g.runner.node_id, data["node"])

    def test_ascii_mode(self):
        g = self.make()
        g.settings["ascii"] = 1
        start_game(g)
        g.card = None
        g.draw()
        chars = set(c[0] for c in g.screen.cells)
        self.assertTrue(chars & set(".:-=+*#%@"))

    def test_softlock_guard(self):
        g = self.make()
        start_game(g)
        play(g, PICKS_PARTITURA, limit=8)
        for _ in range(10):
            g.step(["SPACE"], render=False)
        self.assertIsNotNone(g.runner)

    def test_layout_metrics(self):
        for rows in (30, 34, 40):
            L = Layout(120, rows)
            self.assertGreater(L.box_top, 0)
            self.assertEqual(L.box_top + L.box_h, rows)
            self.assertGreaterEqual(L.text_lines, 3)


if __name__ == "__main__":
    unittest.main()
