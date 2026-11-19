import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from story.content import NODES, START
from engine.story_runner import Runner


class TestRunner(unittest.TestCase):
    def test_choice_effects(self):
        r = Runner(NODES, START)
        r.enter("p_3", apply=False)
        self.assertTrue(r.choose(1))
        self.assertEqual(r.stats["desire"], 1)
        self.assertIn("curious", r.flags)

    def test_clamp(self):
        r = Runner(NODES, START)
        r.apply_effects({"desire": 99, "trust": -99})
        self.assertEqual(r.stats["desire"], 10)
        self.assertEqual(r.stats["trust"], 0)

    def test_locked_choice(self):
        r = Runner(NODES, START)
        r.enter("c3_8", apply=False)
        self.assertFalse(r.choice_enabled(r.current_choices()[0]))
        self.assertFalse(r.choose(0))
        self.assertEqual(r.node_id, "c3_8")
        self.assertTrue(r.choose(1))
        self.assertEqual(r.node_id, "end_cadence_a")

    def test_unlocked_ending(self):
        r = Runner(NODES, START)
        r.enter("c3_8", apply=False)
        r.stats["desire"] = 8
        r.flags.add("kiss")
        self.assertTrue(r.choice_enabled(r.current_choices()[0]))
        self.assertTrue(r.choose(0))
        self.assertEqual(r.node_id, "end_partitura_a")

    def test_save_roundtrip(self):
        r = Runner(NODES, START)
        r.enter("p_6", apply=False)
        r.stats.update({"trust": 3, "desire": 4, "suspicion": 2})
        r.flags.add("e:score")
        r.name = "Аня"
        data = r.to_save()
        r2 = Runner(NODES, START, state=data)
        self.assertEqual(r2.node_id, "p_6")
        self.assertEqual(r2.stats["desire"], 4)
        self.assertEqual(r2.name, "Аня")
        self.assertIn("e:score", r2.flags)

    def test_ending_resolution(self):
        r = Runner(NODES, START)
        r.enter("c3_8", apply=False)
        r.stats["desire"] = 10
        r.flags.add("kiss")
        r.choose(0)
        while not r.ending:
            if not r.advance():
                break
        self.assertEqual(r.ending, "partitura")

    def test_timeout_index(self):
        r = Runner(NODES, START)
        r.enter("p_6", apply=False)
        idx = r.timeout_index()
        self.assertTrue(r.choice_enabled(r.current_choices()[idx]))


if __name__ == "__main__":
    unittest.main()
