import ctypes
import math
import os
import random
import struct
import tempfile
import threading
import time
import wave
from array import array

SR = 16000


def _pick_cache_dir():
    pub = os.environ.get("PUBLIC")
    if pub and os.path.isdir(pub):
        p = os.path.join(pub, "HannibalVN_audio")
        try:
            os.makedirs(p, exist_ok=True)
            probe = os.path.join(p, ".probe")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return p
        except Exception:
            pass
    p = os.path.join(tempfile.gettempdir(), "HannibalVN_audio")
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass
    return p


CACHE_DIR = _pick_cache_dir()

TRACKS = {
    "cell": ("drone", 5.0, dict(freqs=[55.0, 82.5, 110.0], wobble=0.4, noise=0.035, warm=0.7)),
    "office": ("drone", 5.0, dict(freqs=[73.4, 110.0, 146.8], wobble=0.3, noise=0.02, warm=0.9)),
    "dinner": ("drone", 5.0, dict(freqs=[65.4, 98.0, 130.8, 196.0], wobble=0.25, noise=0.018, warm=1.1)),
    "night": ("drone", 5.0, dict(freqs=[41.2, 61.7, 92.5], wobble=0.6, noise=0.05, warm=0.5)),
    "rain": ("rain", 4.0, dict(level=0.32)),
    "fire": ("fire", 4.0, dict(level=0.4)),
    "heart": ("heart", 1.5, dict()),
    "knock": ("knock", 1.3, dict()),
    "door": ("door", 1.4, dict()),
    "clink": ("clink", 0.9, dict()),
    "pen": ("pen", 1.0, dict()),
    "thud": ("thud", 1.0, dict()),
    "chair": ("chair", 0.9, dict()),
    "breath": ("breath", 1.6, dict()),
}


def _write(name, samples, fade=0.12):
    os.makedirs(CACHE_DIR, exist_ok=True)
    n = len(samples)
    f = int(SR * fade)
    if f > 4 and n > f * 3:
        mixed = array("h", samples[: n - f])
        for i in range(f):
            t = i / f
            mixed[i] = int(samples[i] * t + samples[n - f + i] * (1.0 - t))
        samples = mixed
    peak = 1
    for v in samples:
        av = abs(v)
        if av > peak:
            peak = av
    k = 0.72 * 32767.0 / peak if peak > 0 else 0.0
    path_tmp = os.path.join(CACHE_DIR, name + ".tmp")
    path = os.path.join(CACHE_DIR, name + ".wav")
    with wave.open(path_tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        buf = array("h", (int(v * k) for v in samples))
        w.writeframes(buf.tobytes())
    os.replace(path_tmp, path)
    return path


def _drone(dur, freqs, wobble=0.3, noise=0.02, warm=1.0):
    n = int(SR * dur)
    rng = random.Random(1919)
    out = array("h", [0]) * n
    phases = [rng.random() * 6.283 for _ in freqs]
    for i in range(n):
        t = i / SR
        v = 0.0
        for k, f in enumerate(freqs):
            mod = 1.0 + 0.004 * math.sin(2 * math.pi * 0.11 * t + k)
            v += math.sin(2 * math.pi * f * t * mod + phases[k])
        v /= len(freqs)
        lfo = 0.8 + 0.2 * math.sin(2 * math.pi * 0.07 * t + 0.5)
        nz = (rng.random() * 2.0 - 1.0) * noise
        s = (v * lfo * warm + nz) * 0.5
        out[i] = int(max(-1.0, min(1.0, s)) * 28000)
    return out


def _rain(dur, level=0.3):
    n = int(SR * dur)
    rng = random.Random(77)
    out = array("h", [0]) * n
    lp = 0.0
    for i in range(n):
        t = i / SR
        nz = rng.random() * 2.0 - 1.0
        lp = lp * 0.72 + nz * 0.28
        drop = 0.0
        if rng.random() < 0.0022:
            drop = (rng.random() * 2.0 - 1.0) * 0.7
        s = (lp * 0.55 + nz * 0.25 + drop) * level
        out[i] = int(max(-1.0, min(1.0, s)) * 28000)
    return out


def _fire(dur, level=0.4):
    n = int(SR * dur)
    rng = random.Random(31)
    out = array("h", [0]) * n
    env = 0.0
    for i in range(n):
        if rng.random() < 0.0009:
            env = rng.uniform(0.5, 1.0)
        env *= 0.9993
        nz = rng.random() * 2.0 - 1.0
        s = (nz * 0.30 * env + (rng.random() * 2.0 - 1.0) * 0.05) * level
        out[i] = int(max(-1.0, min(1.0, s)) * 28000)
    return out


def _heart():
    n = int(SR * 1.5)
    out = array("h", [0]) * n
    for start, amp in ((0.05, 1.0), (0.34, 0.75), (0.72, 0.5)):
        s0 = int(SR * start)
        for i in range(int(SR * 0.22)):
            if s0 + i >= n:
                break
            t = i / SR
            env = math.exp(-t * 26.0)
            v = math.sin(2 * math.pi * (48.0 + 40.0 * math.exp(-t * 30.0)) * t) * env
            out[s0 + i] += int(v * amp * 26000)
    return out


def _knock():
    n = int(SR * 1.3)
    out = array("h", [0]) * n
    rng = random.Random(9)
    for start in (0.02, 0.26, 0.50):
        s0 = int(SR * start)
        for i in range(int(SR * 0.16)):
            if s0 + i >= n:
                break
            t = i / SR
            env = math.exp(-t * 42.0)
            v = (math.sin(2 * math.pi * 96 * t) * 0.8 + (rng.random() * 2 - 1) * 0.2) * env
            out[s0 + i] += int(v * 24000)
    return out


def _door():
    n = int(SR * 1.4)
    out = array("h", [0]) * n
    rng = random.Random(12)
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 9.0)
        creak = math.sin(2 * math.pi * (180 + 60 * math.sin(2 * math.pi * 2.3 * t)) * t) * 0.18
        nz = (rng.random() * 2 - 1) * 0.25
        thud = math.sin(2 * math.pi * 62 * t) * math.exp(-t * 16) * 0.9
        s = (thud + (creak + nz) * env) * 0.8
        out[i] = int(max(-1.0, min(1.0, s)) * 26000)
    return out


def _clink():
    n = int(SR * 0.9)
    out = array("h", [0]) * n
    rng = random.Random(4)
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 14.0)
        v = (math.sin(2 * math.pi * 2310 * t) * 0.5 + math.sin(2 * math.pi * 3170 * t) * 0.3 +
             math.sin(2 * math.pi * 1210 * t) * 0.2 + (rng.random() * 2 - 1) * 0.15)
        out[i] = int(max(-1.0, min(1.0, v * env * 0.8)) * 26000)
    return out


def _pen():
    n = int(SR * 1.0)
    out = array("h", [0]) * n
    rng = random.Random(15)
    lp = 0.0
    for i in range(n):
        t = i / SR
        nz = rng.random() * 2 - 1
        lp = lp * 0.5 + nz * 0.5
        hp = nz - lp * 0.4
        env = 0.2 + 0.8 * abs(math.sin(2 * math.pi * 5.5 * t))
        scratch = hp * env * 0.25
        out[i] = int(max(-1.0, min(1.0, scratch)) * 26000)
    return out


def _thud():
    n = int(SR * 1.0)
    out = array("h", [0]) * n
    rng = random.Random(21)
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 18.0)
        v = math.sin(2 * math.pi * 55 * t) * env + (rng.random() * 2 - 1) * env * 0.2
        out[i] = int(max(-1.0, min(1.0, v)) * 30000)
    return out


def _chair():
    n = int(SR * 0.9)
    out = array("h", [0]) * n
    rng = random.Random(28)
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 8.0)
        v = math.sin(2 * math.pi * (120 + 40 * math.sin(t * 22)) * t) * 0.35
        v += (rng.random() * 2 - 1) * 0.12
        out[i] = int(max(-1.0, min(1.0, v * env)) * 24000)
    return out


def _breath():
    n = int(SR * 1.6)
    out = array("h", [0]) * n
    rng = random.Random(33)
    lp = 0.0
    for i in range(n):
        t = i / SR
        env = math.sin(math.pi * min(1.0, t / 1.3)) ** 2
        nz = rng.random() * 2 - 1
        lp = lp * 0.86 + nz * 0.14
        s = lp * env * 0.6
        out[i] = int(max(-1.0, min(1.0, s)) * 20000)
    return out


def _generate_one(name, spec):
    kind, dur, kw = spec
    if kind == "drone":
        samples = _drone(dur, **kw)
    elif kind == "rain":
        samples = _rain(dur, **kw)
    elif kind == "fire":
        samples = _fire(dur, **kw)
    elif kind == "heart":
        samples = _heart()
    elif kind == "knock":
        samples = _knock()
    elif kind == "door":
        samples = _door()
    elif kind == "clink":
        samples = _clink()
    elif kind == "pen":
        samples = _pen()
    elif kind == "thud":
        samples = _thud()
    elif kind == "chair":
        samples = _chair()
    elif kind == "breath":
        samples = _breath()
    else:
        samples = array("h", [0]) * int(SR * dur)
    return _write(name, samples)


def _mci(cmd):
    try:
        return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, 0) == 0
    except Exception:
        return False


class Audio:
    def __init__(self, enabled=True, volume=70):
        self.enabled = bool(enabled)
        self.volume = volume
        self.paths = {}
        self.ambient = None
        self.ambient_pending = None
        self._ambient_alias = None
        self._sfx_alias = 0
        self._ready = threading.Event()
        self._mci_ok = True
        self._last_retry = 0.0
        t = threading.Thread(target=self._work, daemon=True)
        t.start()

    def _work(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        for name, spec in TRACKS.items():
            path = os.path.join(CACHE_DIR, name + ".wav")
            try:
                if not os.path.exists(path) or os.path.getsize(path) < 2000:
                    _generate_one(name, spec)
                self.paths[name] = path
            except Exception:
                pass
        self._ready.set()

    def ready_track(self, name):
        p = self.paths.get(name)
        if p and os.path.exists(p):
            return p
        p2 = os.path.join(CACHE_DIR, name + ".wav")
        if name in self.paths and os.path.exists(p2):
            return p2
        return None

    def _apply_volume(self, alias):
        v = int(max(0, min(100, self.volume)) * 10)
        _mci(f"setaudio {alias} volume to {v}")

    def play_ambient(self, name):
        if not self.enabled:
            return
        if name == self.ambient:
            return
        self.ambient = name
        self.ambient_pending = name
        self._start_ambient()

    def _start_ambient(self):
        if not self.enabled or not self.ambient_pending:
            return
        name = self.ambient_pending
        path = self.ready_track(name)
        if not path:
            return
        if self._ambient_alias:
            _mci(f"stop {self._ambient_alias}")
            _mci(f"close {self._ambient_alias}")
            self._ambient_alias = None
        alias = "amb"
        ok = _mci(f'open "{path}" type waveaudio alias {alias}')
        if not ok:
            self._mci_ok = False
            self.ambient_pending = None
            return
        self._apply_volume(alias)
        _mci(f"play {alias} repeat")
        self._ambient_alias = alias
        self.ambient_pending = None

    def stop_ambient(self):
        self.ambient = None
        self.ambient_pending = None
        if self._ambient_alias:
            _mci(f"stop {self._ambient_alias}")
            _mci(f"close {self._ambient_alias}")
            self._ambient_alias = None

    def sfx(self, name):
        if not self.enabled:
            return
        path = self.ready_track(name)
        if not path:
            return
        self._sfx_alias = (self._sfx_alias + 1) % 4
        alias = f"sfx{self._sfx_alias}"
        _mci(f"close {alias}")
        if not _mci(f'open "{path}" type waveaudio alias {alias}'):
            return
        self._apply_volume(alias)
        _mci(f"play {alias}")
        return

    def update(self):
        if not self.enabled:
            return
        now = time.perf_counter()
        if self.ambient_pending and now - self._last_retry > 0.4:
            self._last_retry = now
            self._start_ambient()

    def set_volume(self, v):
        self.volume = v
        if self._ambient_alias:
            self._apply_volume(self._ambient_alias)

    def shutdown(self):
        self.stop_ambient()
        for i in range(4):
            _mci(f"close sfx{i}")
