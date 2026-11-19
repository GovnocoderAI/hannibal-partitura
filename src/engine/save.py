import json
import os
import time

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HannibalVN")
SAVE_DIR = os.path.join(APP_DIR, "saves")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
AUTOSAVE = "auto"
SLOTS = ("1", "2", "3")

DEFAULT_SETTINGS = {
    "text_speed": 1,
    "sound": 1,
    "ambient": 1,
    "animations": 1,
    "grain": 1,
    "ascii": 0,
    "volume": 70,
}


def ensure_dirs():
    os.makedirs(SAVE_DIR, exist_ok=True)


def _write_json(path, data):
    ensure_dirs()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    data = _read_json(SETTINGS_PATH)
    if isinstance(data, dict):
        for k in DEFAULT_SETTINGS:
            if k in data:
                s[k] = data[k]
    return s


def save_settings(settings):
    try:
        _write_json(SETTINGS_PATH, settings)
    except Exception:
        pass


def slot_path(slot):
    return os.path.join(SAVE_DIR, f"slot_{slot}.json")


def save_game(slot, state):
    data = dict(state)
    data["timestamp"] = time.time()
    try:
        _write_json(slot_path(slot), data)
        return True
    except Exception:
        return False


def load_game(slot):
    data = _read_json(slot_path(slot))
    if isinstance(data, dict) and "node" in data:
        return data
    return None


def delete_slot(slot):
    try:
        os.remove(slot_path(slot))
    except Exception:
        pass


def slot_info(slot):
    data = _read_json(slot_path(slot))
    if not isinstance(data, dict):
        return None
    return {
        "name": data.get("name", "?"),
        "chapter": data.get("chapter", ""),
        "timestamp": data.get("timestamp", 0),
        "playtime": data.get("playtime", 0),
        "slot": slot,
    }


def all_slots():
    return {s: slot_info(s) for s in (AUTOSAVE,) + SLOTS}


def latest_slot():
    best = None
    for s in (AUTOSAVE,) + SLOTS:
        info = slot_info(s)
        if info and (best is None or info["timestamp"] > best["timestamp"]):
            best = info
    return best
