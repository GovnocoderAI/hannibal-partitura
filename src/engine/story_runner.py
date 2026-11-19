import time

STAT_KEYS = ("trust", "desire", "suspicion")


def evidence_count(flags):
    return sum(1 for f in flags if f.startswith("e:"))


class Runner:
    def __init__(self, nodes, start, state=None):
        self.nodes = nodes
        self.start = start
        self.node_id = None
        self.name = "Вера"
        self.stats = {k: 0 for k in STAT_KEYS}
        self.flags = set()
        self.chapter = ""
        self.history = []
        self.seen = set()
        self.playtime = 0.0
        self.page = 0
        self.pages = []
        self.speaker = None
        self.ending = None
        self.last_effects = {}
        self._last_tick = time.perf_counter()
        if state:
            self.from_save(state)
        else:
            self.reset()

    def reset(self, name="Вера", start=None):
        self.name = name or "Вера"
        self.stats = {k: 0 for k in STAT_KEYS}
        self.flags = set()
        self.chapter = ""
        self.history = []
        self.seen = set()
        self.playtime = 0.0
        self.ending = None
        self.enter(start or self.start, apply=True)

    def node(self):
        return self.nodes.get(self.node_id, {})

    def fmt(self, text):
        return text.replace("{name}", self.name)

    def tick(self):
        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now
        if dt > 0 and dt < 5:
            self.playtime += dt

    def apply_effects(self, eff):
        if not eff:
            return {}
        changed = {}
        for k in STAT_KEYS:
            if k in eff:
                old = self.stats.get(k, 0)
                val = max(0, min(10, old + eff[k]))
                if val != old:
                    changed[k] = val - old
                self.stats[k] = val
        for f in eff.get("flags", []):
            if f not in self.flags:
                self.flags.add(f)
                changed["flag"] = f
        for f in eff.get("clear", []):
            self.flags.discard(f)
        return changed

    def cond_ok(self, cond):
        if not cond:
            return True
        for k in STAT_KEYS:
            if cond.get(k + "_min") is not None and self.stats[k] < cond[k + "_min"]:
                return False
            if cond.get(k + "_max") is not None and self.stats[k] > cond[k + "_max"]:
                return False
        for f in cond.get("flags", []):
            if f not in self.flags:
                return False
        for f in cond.get("not_flags", []):
            if f in self.flags:
                return False
        if cond.get("evidence_min") is not None and evidence_count(self.flags) < cond["evidence_min"]:
            return False
        return True

    def choose_text(self, node):
        for variant in node.get("variants", []):
            if self.cond_ok(variant.get("if")):
                return variant.get("text", node.get("text", []))
        return node.get("text", [])

    def enter(self, node_id, apply=True, record=True):
        if node_id not in self.nodes:
            node_id = "ending_silence"
        self.node_id = node_id
        node = self.nodes[self.node_id]
        self.ending = None
        if apply:
            self.last_effects = self.apply_effects(node.get("effects"))
        if node.get("chapter"):
            self.chapter = node["chapter"]
        text_paras = [self.fmt(t) for t in self.choose_text(node)]
        self.pages = text_paras
        self.page = 0
        self.speaker = node.get("who")
        self.seen.add(node_id)
        if text_paras and record:
            self.history.append((node.get("who"), " ".join(text_paras)))
        if len(self.history) > 240:
            self.history = self.history[-240:]
        if node.get("ending"):
            self.ending = node["ending"]

    def current_choices(self):
        node = self.node()
        return node.get("choices", [])

    def choice_enabled(self, ch):
        return self.cond_ok(ch.get("req"))

    def next_target(self, node):
        for rule in node.get("goto_if", []):
            if self.cond_ok(rule.get("if")):
                return rule.get("goto")
        return node.get("next")

    def advance(self):
        if self.ending:
            return False
        node = self.node()
        if node.get("choices"):
            return False
        target = self.next_target(node)
        if target:
            self.enter(target, apply=True)
            return True
        return False

    def choose(self, index):
        node = self.node()
        choices = node.get("choices", [])
        if index < 0 or index >= len(choices):
            return False
        ch = choices[index]
        if not self.choice_enabled(ch):
            return False
        choice_text = self.fmt(ch.get("text", ""))
        self.history.append((None, "› " + choice_text))
        self.last_effects = self.apply_effects(ch.get("effects"))
        target = ch.get("goto") or self.next_target(node)
        if target:
            self.enter(target, apply=True)
        elif node.get("ending"):
            self.ending = node["ending"]
            self.node_id = self.node_id
        return True

    def timeout_index(self):
        node = self.node()
        choices = node.get("choices", [])
        for i, ch in enumerate(choices):
            if ch.get("timeout") and self.choice_enabled(ch):
                return i
        for i, ch in enumerate(choices):
            if self.choice_enabled(ch):
                return i
        return 0

    def to_save(self):
        return {
            "node": self.node_id,
            "name": self.name,
            "stats": dict(self.stats),
            "flags": sorted(self.flags),
            "chapter": self.chapter,
            "history": [[w, t] for (w, t) in self.history[-120:]],
            "seen": sorted(self.seen)[-400:],
            "playtime": round(self.playtime, 1),
            "ending": self.ending,
            "version": 2,
        }

    def from_save(self, data):
        self.name = data.get("name", "Вера")
        self.stats = {k: int(data.get("stats", {}).get(k, 0)) for k in STAT_KEYS}
        self.flags = set(data.get("flags", []))
        self.chapter = data.get("chapter", "")
        self.history = [(w, t) for (w, t) in data.get("history", [])]
        self.seen = set(data.get("seen", []))
        self.playtime = float(data.get("playtime", 0.0))
        self.node_id = data.get("node", self.start)
        if self.node_id not in self.nodes:
            self.node_id = self.start
        self.enter(self.node_id, apply=False, record=False)
        self.ending = data.get("ending") or self.node().get("ending")
