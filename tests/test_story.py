import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from story.content import NODES, START, ENDINGS
from story.validate import validate


class TestStory(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(), [])

    def test_start_exists(self):
        self.assertIn(START, NODES)

    def test_three_endings(self):
        found = {n.get("ending") for n in NODES.values() if n.get("ending")}
        self.assertEqual(found, set(ENDINGS))

    def test_choices_have_text(self):
        for nid, node in NODES.items():
            for ch in node.get("choices", []):
                self.assertTrue(ch.get("text"), nid)
                self.assertLessEqual(len(ch["text"]), 70, nid)

    def test_no_empty_text(self):
        for nid, node in NODES.items():
            if node.get("ending") is None:
                self.assertTrue(node.get("text"), nid)

    def test_node_count(self):
        self.assertGreaterEqual(len(NODES), 50)


if __name__ == "__main__":
    unittest.main()
