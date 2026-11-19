import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from engine import save as savemod


class TestSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hannibal_test_")
        self._save_dir = savemod.SAVE_DIR
        self._settings = savemod.SETTINGS_PATH
        savemod.SAVE_DIR = os.path.join(self.tmp, "saves")
        savemod.SETTINGS_PATH = os.path.join(self.tmp, "settings.json")

    def tearDown(self):
        savemod.SAVE_DIR = self._save_dir
        savemod.SETTINGS_PATH = self._settings

    def test_roundtrip(self):
        state = {"node": "c1_1", "name": "Тест", "playtime": 12.3, "chapter": "I"}
        self.assertTrue(savemod.save_game("1", state))
        data = savemod.load_game("1")
        self.assertEqual(data["node"], "c1_1")
        self.assertEqual(data["name"], "Тест")
        info = savemod.slot_info("1")
        self.assertEqual(info["name"], "Тест")
        self.assertEqual(info["chapter"], "I")

    def test_empty_slot(self):
        self.assertIsNone(savemod.load_game("2"))
        self.assertIsNone(savemod.slot_info("2"))

    def test_delete(self):
        savemod.save_game("3", {"node": "p_1"})
        savemod.delete_slot("3")
        self.assertIsNone(savemod.load_game("3"))

    def test_latest(self):
        savemod.save_game("1", {"node": "p_1", "playtime": 1})
        savemod.save_game("2", {"node": "p_2", "playtime": 2})
        info = savemod.latest_slot()
        self.assertIsNotNone(info)
        self.assertEqual(info["slot"], "2")

    def test_settings(self):
        s = savemod.load_settings()
        s["volume"] = 33
        s["text_speed"] = 3
        savemod.save_settings(s)
        s2 = savemod.load_settings()
        self.assertEqual(s2["volume"], 33)
        self.assertEqual(s2["text_speed"], 3)


if __name__ == "__main__":
    unittest.main()
