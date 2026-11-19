import math
import os
import random
import sys
import time

from engine.term import Console, Screen, rgb, mix_int, scale_int
from engine.story_runner import Runner, STAT_KEYS, evidence_count
from engine import save as savemod
from engine.audio import Audio
from art.faces import get_portrait, EXPRESSIONS
from art.scenes_art import get_bg
from story import content as STORY

GOLD = rgb(198, 168, 112)
GOLD_DIM = rgb(122, 102, 70)
GOLD_PALE = rgb(226, 206, 158)
PARCH = rgb(222, 210, 190)
PARCH_DIM = rgb(164, 156, 142)
RED = rgb(158, 42, 40)
RED_DARK = rgb(54, 12, 14)
RED_SOFT = rgb(112, 34, 32)
ASH = rgb(120, 114, 106)
INK = rgb(10, 9, 10)
PANEL_TINT = rgb(12, 11, 12)
WHITE = rgb(238, 232, 220)

BOX = ("┌", "┐", "└", "┘", "─", "│")
BOX2 = ("╔", "╗", "╚", "╝", "═", "║")

SPEAKERS = {
    "hannibal": "ГАННИБАЛ",
    "rurke": "АГЕНТ РУРК",
    "chilton": "ДОКТОР ЧИЛТОН",
    "composer": "КОМПОЗИТОР",
    "heroine": "{name}",
    None: "",
}

SPEAKER_COLORS = {
    "hannibal": GOLD_PALE,
    "rurke": rgb(150, 160, 176),
    "chilton": rgb(178, 168, 146),
    "composer": rgb(158, 150, 156),
    "heroine": rgb(226, 202, 184),
    None: PARCH_DIM,
}

AMBIENT_BY_BG = {
    "cell": "cell",
    "corridor": "cell",
    "office": "office",
    "dinner": "dinner",
    "snow": "night",
    "house": "fire",
    "memory": "office",
    "black": "night",
    "title": "cell",
}

SPEEDS = (20.0, 38.0, 78.0, 100000.0)
SPEED_NAMES = ("медленно", "обычно", "быстро", "мгновенно")

BIG_FONT = {
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    " ": ("00000",) * 7,
}


def wrap(text, width):
    lines = []
    for raw in str(text).split("\n"):
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        cur = ""
        for word in raw.split():
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= width:
                cur += " " + word
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def clips(text, width):
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


class Layout:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.box_w = min(cols - 2, 116)
        self.x0 = (cols - self.box_w) // 2
        self.x1 = self.x0 + self.box_w - 1
        if rows >= 38:
            self.text_lines = 5
        elif rows >= 34:
            self.text_lines = 4
        else:
            self.text_lines = 3
        self.box_h = self.text_lines + 6
        self.box_top = rows - self.box_h
        self.text_x = self.x0 + 2
        self.text_w = self.box_w - 4
        if rows >= 38:
            self.ps = 1.0
        elif rows >= 34:
            self.ps = 0.9
        else:
            self.ps = 0.8
        self.portrait_oy = self.box_top * 2 - int(55 * self.ps) - (3 if self.ps >= 0.95 else 1)
        self.portrait_ox = (cols - int(120 * self.ps)) // 2
        self.bg_scale = max(cols / 120.0, (rows * 2) / 80.0)
        self.bg_ox = (cols - 120 * self.bg_scale) / 2.0
        self.bg_oy = (rows * 2 - 80 * self.bg_scale) / 2.0


class NullAudio:
    enabled = False
    volume = 0

    def play_ambient(self, name):
        pass

    def stop_ambient(self):
        pass

    def sfx(self, name):
        pass

    def update(self):
        pass

    def set_volume(self, v):
        pass

    def shutdown(self):
        pass


class DummyConsole:
    def __init__(self):
        self.out = []

    def setup(self):
        pass

    def restore(self):
        pass

    def write(self, s):
        self.out.append(s)

    def clear(self):
        pass

    def size(self):
        return 120, 40

    def poll(self):
        return []


class Game:
    def __init__(self, headless=False, console=None, audio=None, width=None, height=None):
        self.headless = headless
        self.console = console or (DummyConsole() if headless else Console())
        self.settings = savemod.load_settings()
        if audio is not None:
            self.audio = audio
        elif headless:
            self.audio = NullAudio()
        else:
            self.audio = Audio(enabled=bool(self.settings.get("sound", 1)),
                               volume=self.settings.get("volume", 70))
        if width and height:
            self.cols, self.rows = width, height
        else:
            self.cols, self.rows = self.console.size()
        self.layout = Layout(self.cols, self.rows)
        self.screen = Screen(self.cols, self.rows)
        self.screen.dirty_all = True
        self.runner = None
        self.mode = "disclaimer"
        self.running = True
        self.t = 0.0
        self.frame = 0
        self.fade_t = 1.0
        self.fx = []
        self.type_i = 0.0
        self.type_acc = 0.0
        self.uipages = []
        self.uipage = 0
        self.sel = 0
        self.timer_t = None
        self.timer_total = 0.0
        self.choice_shown_t = -1.0
        self.toasts = []
        self.card = None
        self.card_t = 0.0
        self.scroll = 0
        self.menu_sel = 0
        self.slot_mode = "load"
        self.slot_sel = 0
        self.settings_sel = 0
        self.prev_mode = "title"
        self.name_input = ""
        self.ending_shown = False
        self._shown_node = None
        self._shown_page = 0
        self._bg_name = "title"
        self.show = None
        self.expr = "neutral"
        self.blink_next = 2.0
        self.blink_t = -1.0
        self.mouth_phase = 0
        self.last_type_char = 0
        self.audio_amb = None
        self.chapter_glow = 0.0
        self.stats_echo = 0.0
        self.random = random.Random(4)
        self._bg_cells_cache = {}
        self._overlay_cache = {}

    def set_ambient(self, name):
        if not self.settings.get("ambient", 1):
            self.audio.stop_ambient()
            return
        self.audio.play_ambient(name)

    def start(self):
        self.console.setup()
        self.set_ambient("cell")
        try:
            last = time.perf_counter()
            while self.running:
                now = time.perf_counter()
                dt = now - last
                last = now
                if dt > 0.12:
                    dt = 0.12
                self.t += dt
                self.frame += 1
                events = self.console.poll()
                self.handle(events, dt)
                if not self.running:
                    break
                self.draw()
                self.screen.present(self.console)
                self.audio.update()
                spent = time.perf_counter() - now
                if spent < 1.0 / 30.0:
                    time.sleep(1.0 / 30.0 - spent)
        finally:
            try:
                self.audio.shutdown()
            except Exception:
                pass
            self.console.restore()

    def step(self, events=(), dt=1.0 / 30.0, render=True):
        self.t += dt
        self.frame += 1
        self.handle(list(events), dt)
        if self.running and render:
            self.draw()

    def set_mode(self, mode):
        self.mode = mode
        self.screen.dirty_all = True

    def new_game(self, name):
        self.runner = Runner(STORY.NODES, STORY.START)
        self.runner.reset(name)
        self._shown_node = None
        self.set_mode("game")
        self._bg_name = self.runner.node().get("bg", "cell")
        self.fade_t = 0.0
        self.ending_shown = False
        self.set_ambient(AMBIENT_BY_BG.get(self._bg_name, "cell"))
        self.sync_node(force=True)

    def load_state(self, state):
        self.runner = Runner(STORY.NODES, STORY.START, state=state)
        self._shown_node = None
        self.set_mode("game")
        self._bg_name = self.runner.node().get("bg", "cell")
        self.fade_t = 0.0
        self.ending_shown = False
        self.sync_node(force=True)

    def continue_game(self):
        info = savemod.latest_slot()
        if not info:
            return False
        data = savemod.load_game(info["slot"])
        if not data:
            return False
        self.load_state(data)
        self.set_ambient(AMBIENT_BY_BG.get(self._bg_name, "cell"))
        return True

    def current_lines(self):
        if not self.runner:
            return []
        paras = self.runner.pages
        lines = []
        for i, p in enumerate(paras):
            if i > 0:
                lines.append("")
            lines.extend(wrap(p, self.layout.text_w))
        return lines

    def sync_node(self, force=False):
        r = self.runner
        if not r or (r.node_id == self._shown_node and not force):
            return
        node = r.node()
        self._shown_node = r.node_id
        self._shown_page = 0
        self.ending_shown = False
        width = self.layout.text_w
        n = self.layout.text_lines
        blocks = [wrap(p, width) for p in r.pages]
        blocks = [b for b in blocks if b]
        pages = []
        cur = []
        for block in blocks:
            need = len(block) + (1 if cur else 0)
            if len(cur) + need <= n:
                if cur:
                    cur.append("")
                cur.extend(block)
            else:
                if cur:
                    pages.append(cur)
                    cur = []
                block = list(block)
                while len(block) > n:
                    pages.append(block[:n])
                    block = block[n:]
                if block:
                    cur = block
        if cur:
            pages.append(cur)
        if len(pages) >= 2 and len(pages[-1]) <= 1 and "" in pages[-2]:
            last = pages.pop()
            pages[-1].remove("")
            pages[-1].extend(last)
        for p in pages:
            while p and not p[0].strip():
                p.pop(0)
            while p and not p[-1].strip():
                p.pop()
        pages = [p for p in pages if p]
        self.uipages = pages or [[""]]
        self.uipage = 0
        self.type_i = 0.0
        self.type_acc = 0.0
        self.sel = 0
        self.choice_shown_t = -1.0
        bgname = node.get("bg", self._bg_name)
        if bgname != self._bg_name:
            self._bg_name = bgname
            self.fade_t = 0.0
        show = node.get("show", "keep")
        if show == "none":
            self.show = None
        elif isinstance(show, (list, tuple)) and len(show) >= 2:
            self.show = (show[0], show[1])
        elif isinstance(show, str):
            self.show = (show, node.get("expr", "neutral"))
        self.expr = node.get("expr", self.show[1] if self.show else "neutral")
        if self.expr not in EXPRESSIONS:
            self.expr = "neutral"
        amb = node.get("amb") or AMBIENT_BY_BG.get(self._bg_name)
        if amb and amb != self.audio_amb:
            self.audio_amb = amb
            if self.settings.get("ambient", 1):
                self.set_ambient(amb)
        if node.get("sfx"):
            self.audio.sfx(node["sfx"])
        for f in node.get("fx", []):
            self.add_fx(f)
        if node.get("chapter_start"):
            self.card = {
                "title": node.get("chapter_start"),
                "subtitle": node.get("chapter_sub", ""),
                "num": node.get("chapter_num", ""),
            }
            self.card_t = 0.0
        eff = r.last_effects or {}
        for k in STAT_KEYS:
            if k in eff and eff[k]:
                names = {"trust": "доверие", "desire": "желание", "suspicion": "подозрение"}
                self.toast(("+" if eff[k] > 0 else "") + str(eff[k]) + " " + names[k], k)
        if node.get("timer"):
            self.timer_total = float(node["timer"])
            self.timer_t = self.timer_total
            self.audio.sfx("heart")
        else:
            self.timer_t = None
        if self.mode == "game":
            savemod.save_game("auto", r.to_save())

    def add_fx(self, kind):
        if kind == "shake":
            self.fx.append({"type": "shake", "t": 0.0, "dur": 0.55})
        elif kind == "flash":
            self.fx.append({"type": "flash", "t": 0.0, "dur": 0.5})
        elif kind == "slow":
            self.fx.append({"type": "slow", "t": 0.0, "dur": 1.2})

    def toast(self, text, color_key="trust"):
        col = {"trust": rgb(150, 178, 150), "desire": rgb(198, 120, 118), "suspicion": rgb(170, 160, 120)}.get(color_key, GOLD)
        self.toasts.append({"text": text, "t": 0.0, "dur": 2.4, "col": col})

    def update_fx(self, dt):
        for f in self.fx:
            f["t"] += dt
        self.fx = [f for f in self.fx if f["t"] < f["dur"]]
        for ts in self.toasts:
            ts["t"] += dt
        self.toasts = [x for x in self.toasts if x["t"] < x["dur"]]
        if self.card:
            self.card_t += dt

    def brightness(self):
        base = min(1.0, self.fade_t / 0.55)
        return 0.12 + 0.88 * (base ** 1.3)

    def bg_cells(self, bgname, brightness=1.0, grain=0.0, seed=1):
        key = (bgname, self.cols, self.rows, bool(self.settings.get("ascii", 0)),
               round(brightness, 2), round(grain, 3), seed)
        hit = self._bg_cells_cache.get(key)
        if hit is not None:
            return hit
        L = self.layout
        saved = self.screen.cells
        self.screen.cells = [(" ", rgb(8, 8, 10), rgb(0, 0, 0))] * (self.cols * self.rows)
        self.screen.art(get_bg(bgname), int(L.bg_ox), int(L.bg_oy), L.bg_scale,
                        ascii_mode=bool(self.settings.get("ascii", 0)))
        if brightness != 1.0 or grain > 0.0:
            self.screen.effects(brightness=brightness, grain=grain, seed=seed)
        cells = list(self.screen.cells)
        self.screen.cells = saved
        if len(self._bg_cells_cache) > 24:
            self._bg_cells_cache.clear()
        self._bg_cells_cache[key] = cells
        return cells

    def flash_amount(self):
        amt = 0.0
        for f in self.fx:
            if f["type"] == "flash":
                k = 1.0 - f["t"] / f["dur"]
                amt = max(amt, k * 0.5)
        return amt

    def shake_offset(self):
        amp = 0
        for f in self.fx:
            if f["type"] == "shake":
                k = 1.0 - f["t"] / f["dur"]
                amp = max(amp, int(3 * k))
        if amp:
            return (self.random.randint(-amp, amp), self.random.randint(-amp, amp))
        return (0, 0)

    def blink_value(self):
        if self.blink_t >= 0:
            self.blink_t += 1.0 / 30.0
            if self.blink_t < 0.06:
                return 0.5
            if self.blink_t < 0.14:
                return 1.0
            if self.blink_t < 0.20:
                return 0.5
            self.blink_t = -1.0
            self.blink_next = self.t + self.random.uniform(2.4, 5.8)
        elif self.t >= self.blink_next:
            self.blink_t = 0.0
        return 0.0

    def mouth_value(self):
        if self.type_i < len(self.current_page_text()):
            self.mouth_phase = 1 if (int(self.type_i) // 2) % 2 == 0 else 2
            return 0.45 + 0.35 * (0.5 + 0.5 * math.sin(self.t * 22.0))
        self.mouth_phase = 0
        return 0.0

    def current_page_text(self):
        if not self.uipages:
            return ""
        return "\n".join(self.uipages[min(self.uipage, len(self.uipages) - 1)])

    def page_char_count(self):
        if not self.uipages:
            return 0
        return sum(len(x) for x in self.uipages[min(self.uipage, len(self.uipages) - 1)])

    def total_pages(self):
        return len(self.uipages)

    def handle_default(self, events, dt):
        pass

    def tick_typing(self, dt):
        speed = SPEEDS[self.settings.get("text_speed", 1)]
        total = self.page_char_count()
        if self.type_i < total:
            self.type_acc += dt * speed
            self.type_i = min(total, self.type_acc)

    def tick_timer(self, dt):
        if self.timer_t is None:
            return
        if self.type_i < self.page_char_count():
            return
        if self.runner is None:
            return
        if self.uipage + 1 < len(self.uipages):
            return
        if not self.runner.current_choices():
            return
        self.timer_t -= dt
        if self.timer_t <= 2.0 and self.timer_t + dt > 2.0:
            self.audio.sfx("heart")
        if self.timer_t <= 0:
            idx = self.runner.timeout_index()
            self.apply_choice(idx)

    def type_finished(self):
        return self.type_i >= self.page_char_count()

    def advance(self):
        r = self.runner
        if r is None:
            return
        if self.type_i < self.page_char_count():
            self.type_i = self.page_char_count()
            self.type_acc = self.type_i
            return
        if self.uipage + 1 < len(self.uipages):
            self.uipage += 1
            self.type_i = 0.0
            self.type_acc = 0.0
            self.audio.sfx("pen")
            return
        if r.ending:
            self.finish_ending()
            return
        node = r.node()
        if node.get("choices"):
            return
        if r.advance():
            self.sync_node(force=True)
            if self.runner.ending and not self.runner.pages:
                self.finish_ending()
        else:
            self.finish_ending()

    def apply_choice(self, idx):
        r = self.runner
        if r is None:
            return
        if idx < 0 or idx >= len(r.current_choices()):
            return
        if not r.choice_enabled(r.current_choices()[idx]):
            self.audio.sfx("thud")
            return
        if r.choose(idx):
            self.timer_t = None
            self.audio.sfx("clink")
            self.sync_node(force=True)
            if self.runner.ending and not self.runner.pages:
                self.finish_ending()

    def finish_ending(self):
        if self.runner and self.runner.ending:
            self.set_mode("ending")
            self.ending_shown = True
            self.audio.stop_ambient()
            self.audio.sfx("heart")
        else:
            self.set_mode("title")
            self.menu_sel = 0

    def handle_game(self, events, dt):
        if self.card is not None and self.card_t > 0.30 and events:
            self.card = None
            return
        for e in events:
            if e in ("ESC",):
                self.prev_mode = "game"
                self.set_mode("pause")
                self.sel = 0
                return
            if e in ("TAB",):
                self.prev_mode = "game"
                self.set_mode("history")
                self.scroll = 0
                return
            if e in ("CTRL_C",):
                self.running = False
                return
            choices = self.runner.current_choices() if self.runner else []
            show_choices = choices and self.type_finished() and self.uipage + 1 >= len(self.uipages)
            if show_choices:
                if e in ("UP", "w", "W", "ц", "Ц"):
                    self.sel = (self.sel - 1) % len(choices)
                    self.audio.sfx("pen")
                elif e in ("DOWN", "s", "S", "ы", "Ы"):
                    self.sel = (self.sel + 1) % len(choices)
                    self.audio.sfx("pen")
                elif e in ("ENTER", "SPACE", "\r"):
                    if self.choice_shown_t >= 0 and self.t - self.choice_shown_t > 0.10:
                        self.apply_choice(self.sel)
                elif e in ("1", "2", "3", "4"):
                    idx = int(e) - 1
                    if idx < len(choices):
                        self.apply_choice(idx)
            else:
                if e in ("ENTER", "SPACE", "RIGHT", "DOWN"):
                    self.advance()

    def handle_disclaimer(self, events, dt):
        for e in events:
            if e in ("ENTER", "SPACE"):
                self.set_mode("title")
                self.set_ambient("cell")
            elif e == "CTRL_C":
                self.running = False

    def handle_title(self, events, dt):
        items = self.title_items()
        for e in events:
            if e in ("UP", "w", "W", "ц", "Ц"):
                self.menu_sel = (self.menu_sel - 1) % len(items)
                self.audio.sfx("pen")
            elif e in ("DOWN", "s", "S", "ы", "Ы"):
                self.menu_sel = (self.menu_sel + 1) % len(items)
                self.audio.sfx("pen")
            elif e in ("ENTER", "SPACE"):
                self.title_action(items[self.menu_sel][0])
            elif e == "CTRL_C":
                self.running = False

    def title_items(self):
        has_save = savemod.latest_slot() is not None
        return [
            ("new", "НОВАЯ ИГРА"),
            ("continue", "ПРОДОЛЖИТЬ" if has_save else "ПРОДОЛЖИТЬ  ·  нет сохранений"),
            ("load", "ЗАГРУЗИТЬ"),
            ("settings", "НАСТРОЙКИ"),
            ("about", "ОБ ИГРЕ"),
            ("exit", "ВЫХОД"),
        ]

    def title_action(self, action):
        if action == "new":
            self.name_input = ""
            self.set_mode("name")
        elif action == "continue":
            if self.continue_game():
                pass
            else:
                self.audio.sfx("thud")
        elif action == "load":
            self.slot_mode = "load"
            self.slot_sel = 0
            self.set_mode("saves")
        elif action == "settings":
            self.prev_mode = "title"
            self.settings_sel = 0
            self.set_mode("settings")
        elif action == "about":
            self.set_mode("about")
        elif action == "exit":
            self.running = False

    def handle_name(self, events, dt):
        for e in events:
            if e == "ESC":
                self.set_mode("title")
            elif e == "ENTER":
                name = self.name_input.strip() or "Вера"
                name = name[:16]
                self.new_game(name)
            elif e == "BACKSPACE":
                self.name_input = self.name_input[:-1]
            elif e == "SPACE":
                if len(self.name_input) < 16:
                    self.name_input += " "
            elif isinstance(e, str) and len(e) == 1 and ord(e) >= 32 and len(self.name_input) < 16:
                self.name_input += e
        self.type_i = 0

    def handle_about(self, events, dt):
        for e in events:
            if e in ("ESC", "ENTER", "SPACE"):
                self.set_mode("title")

    def handle_ending(self, events, dt):
        for e in events:
            if e in ("ENTER", "SPACE", "ESC"):
                self.set_mode("title")
                self.menu_sel = 0
                self.audio_amb = None
                self.set_ambient("cell")
                self._bg_name = "title"

    def handle_history(self, events, dt):
        total = len(self.history_lines())
        for e in events:
            if e in ("ESC", "TAB"):
                self.set_mode(self.prev_mode)
                return
            if e in ("UP", "w", "W"):
                self.scroll = min(max(0, self.scroll - 1), max(0, total - 1))
            elif e in ("DOWN", "s", "S"):
                self.scroll = min(self.scroll + 1, max(0, total - 1))
            elif e == "PGUP":
                self.scroll = max(0, self.scroll - 8)
            elif e == "PGDN":
                self.scroll = min(self.scroll + 8, max(0, total - 1))
            elif e in ("HOME",):
                self.scroll = 0
            elif e in ("END",):
                self.scroll = max(0, total - 1)

    def history_lines(self):
        if not self.runner:
            return []
        width = self.cols - 8
        out = []
        for who, text in self.runner.history:
            name = SPEAKERS.get(who, who) or ""
            name = name.replace("{name}", self.runner.name)
            prefix = (name + ": ") if name else ""
            for i, line in enumerate(wrap(prefix + text, width)):
                out.append(line)
            out.append("")
        return out

    def handle_pause(self, events, dt):
        items = self.pause_items()
        for e in events:
            if e in ("ESC",):
                self.set_mode("game")
                return
            if e in ("UP", "w", "W", "ц", "Ц"):
                self.sel = (self.sel - 1) % len(items)
            elif e in ("DOWN", "s", "S", "ы", "Ы"):
                self.sel = (self.sel + 1) % len(items)
            elif e in ("ENTER", "SPACE"):
                self.pause_action(items[self.sel][0])

    def pause_items(self):
        return [
            ("resume", "ПРОДОЛЖИТЬ"),
            ("save", "СОХРАНИТЬ"),
            ("load", "ЗАГРУЗИТЬ"),
            ("settings", "НАСТРОЙКИ"),
            ("history", "ИСТОРИЯ"),
            ("title", "В ГЛАВНОЕ МЕНЮ"),
            ("exit", "ВЫХОД"),
        ]

    def pause_action(self, action):
        if action == "resume":
            self.set_mode("game")
        elif action == "save":
            self.slot_mode = "save"
            self.slot_sel = 0
            self.prev_mode = "game"
            self.set_mode("saves")
        elif action == "load":
            self.slot_mode = "load"
            self.slot_sel = 0
            self.prev_mode = "game"
            self.set_mode("saves")
        elif action == "settings":
            self.prev_mode = "pause"
            self.settings_sel = 0
            self.set_mode("settings")
        elif action == "history":
            self.prev_mode = "pause"
            self.scroll = 0
            self.set_mode("history")
        elif action == "title":
            self.runner = None
            self.set_mode("title")
            self._bg_name = "title"
            self.menu_sel = 0
            self.audio_amb = None
            self.set_ambient("cell")
        elif action == "exit":
            self.running = False

    def slot_list(self):
        slots = ["auto", "1", "2", "3"]
        return slots

    def handle_saves(self, events, dt):
        slots = self.slot_list()
        for e in events:
            if e == "ESC":
                self.set_mode(self.prev_mode)
                return
            if e in ("UP", "w", "W"):
                self.slot_sel = (self.slot_sel - 1) % len(slots)
            elif e in ("DOWN", "s", "S"):
                self.slot_sel = (self.slot_sel + 1) % len(slots)
            elif e in ("ENTER", "SPACE"):
                slot = slots[self.slot_sel]
                if self.slot_mode == "save":
                    if slot == "auto":
                        self.audio.sfx("thud")
                    else:
                        if self.runner:
                            savemod.save_game(slot, self.runner.to_save())
                            self.audio.sfx("clink")
                            self.set_mode(self.prev_mode)
                else:
                    data = savemod.load_game(slot)
                    if data:
                        self.load_state(data)
                    else:
                        self.audio.sfx("thud")
            elif e in ("d", "D", "в", "В"):
                slot = slots[self.slot_sel]
                if slot != "auto":
                    savemod.delete_slot(slot)

    def settings_rows(self):
        s = self.settings
        return [
            ("text_speed", "СКОРОСТЬ ТЕКСТА", SPEED_NAMES[max(0, min(3, int(s.get("text_speed", 1))))]),
            ("sound", "ЗВУК", "вкл" if s.get("sound", 1) else "выкл"),
            ("ambient", "ЭМБИЕНТ", "вкл" if s.get("ambient", 1) else "выкл"),
            ("animations", "АНИМАЦИИ", "вкл" if s.get("animations", 1) else "выкл"),
            ("grain", "ПЛЁНОЧНОЕ ЗЕРНО", "вкл" if s.get("grain", 1) else "выкл"),
            ("ascii", "ASCII-РЕЖИМ", "вкл" if s.get("ascii", 0) else "выкл"),
            ("volume", "ГРОМКОСТЬ", str(s.get("volume", 70)) + "%"),
        ]

    def handle_settings(self, events, dt):
        rows = self.settings_rows()
        for e in events:
            if e == "ESC":
                savemod.save_settings(self.settings)
                self.set_mode(self.prev_mode)
                return
            if e in ("UP", "w", "W", "ц", "Ц"):
                self.settings_sel = (self.settings_sel - 1) % len(rows)
            elif e in ("DOWN", "s", "S", "ы", "Ы"):
                self.settings_sel = (self.settings_sel + 1) % len(rows)
            elif e in ("LEFT", "RIGHT", "ENTER", "SPACE", "a", "d", "A", "D", "ф", "в"):
                key = rows[self.settings_sel][0]
                delta = -1 if e in ("LEFT", "a", "A", "ф") else 1
                self.change_setting(key, delta)
        self.apply_audio_settings()

    def change_setting(self, key, delta):
        s = self.settings
        if key == "text_speed":
            s["text_speed"] = (int(s.get("text_speed", 1)) + delta) % 4
        elif key == "volume":
            s["volume"] = max(0, min(100, int(s.get("volume", 70)) + delta * 10))
            self.audio.set_volume(s["volume"])
        elif key == "sound":
            s["sound"] = 0 if s.get("sound", 1) else 1
            self.audio.enabled = bool(s["sound"])
            if not s["sound"]:
                self.audio.stop_ambient()
            else:
                self.set_ambient(AMBIENT_BY_BG.get(self._bg_name, "cell"))
        elif key in ("ambient", "animations", "grain", "ascii"):
            s[key] = 0 if s.get(key, 1) else 1
            if key == "ambient":
                if s[key]:
                    self.set_ambient(AMBIENT_BY_BG.get(self._bg_name, "cell"))
                else:
                    self.audio.stop_ambient()
        savemod.save_settings(s)

    def apply_audio_settings(self):
        self.audio.enabled = bool(self.settings.get("sound", 1))

    def handle(self, events, dt):
        self.update_fx(dt)
        self.fade_t = min(1.0, self.fade_t + dt / 0.55)
        if self.mode == "game" and self.runner:
            self.runner.tick()
            self.sync_node()
            self.tick_typing(dt)
            self.tick_timer(dt)
            ch = self.runner.current_choices()
            if ch and self.type_finished() and self.uipage + 1 >= len(self.uipages):
                if self.choice_shown_t < 0:
                    self.choice_shown_t = self.t
            else:
                self.choice_shown_t = -1.0
        fn = getattr(self, "handle_" + self.mode, None)
        if fn:
            fn(events, dt)
        else:
            self.handle_default(events, dt)

    def draw(self):
        if self.headless:
            cols, rows = self.cols, self.rows
        else:
            cols, rows = self.console.size()
        if rows < 28 or cols < 72:
            self.screen.clear()
            msg = "Увеличьте окно терминала — минимум 72×28"
            self.screen.text(max(0, (cols - len(msg)) // 2), max(0, rows // 2), msg[: max(1, cols - 2)], GOLD)
            return
        if (cols, rows) != (self.cols, self.rows):
            self.cols, self.rows = cols, rows
            self.layout = Layout(cols, rows)
            self.screen = Screen(cols, rows)
            self.screen.dirty_all = True
        getattr(self, "draw_" + self.mode, self.draw_default)()

    def draw_default(self):
        self.screen.clear()

    def bg_params(self):
        shake = self.shake_offset()
        if not self.settings.get("animations", 1):
            shake = (0, 0)
        return shake

    def draw_art_layer(self, bgname=None, portrait=True):
        L = self.layout
        s = self.screen
        target = bgname or self._bg_name
        sx, sy = self.bg_params()
        br = self.brightness()
        grain = 0.006 if self.settings.get("grain", 1) else 0.0
        tint = rgb(150, 26, 24)
        flash = self.flash_amount()
        s.cells = list(self.bg_cells(target))
        if portrait and self.show:
            name, expr = self.show
            if expr not in EXPRESSIONS:
                expr = "neutral"
            p = get_portrait(name)
            animations = self.settings.get("animations", 1)
            blink = self.blink_value() if animations else 0.0
            mouth = self.mouth_value() if animations else 0.0
            breath = 0
            if animations:
                breath = 1 if math.sin(self.t * 1.35) > 0.55 else 0
            pox = L.portrait_ox + sx
            poy = L.portrait_oy + sy + breath
            reg = (int(pox), int(poy / 2) - 1,
                   int(pox + 120 * L.ps) + 1, int((poy + 80 * L.ps) / 2) + 1)
            fr = p.frame(expr, blink=blink, mouth=mouth, phase=self.mouth_phase)
            if self.settings.get("ascii", 0):
                s.art(fr, pox, poy, L.ps, region=reg, ascii_mode=True)
            else:
                key = (name, expr, round(blink, 1), round(mouth, 1), self.mouth_phase,
                       pox, poy, round(L.ps, 2), self.cols, self.rows)
                overlay = self._overlay_cache.get(key)
                if overlay is None:
                    overlay = s.art_overlay(fr, pox, poy, L.ps, region=reg)
                    if len(self._overlay_cache) > 64:
                        self._overlay_cache.clear()
                    self._overlay_cache[key] = overlay
                s.apply_overlay(overlay)
        s.effects(brightness=br, tint=tint if flash > 0.02 else None, tint_amt=flash * 0.5,
                  grain=grain, seed=self.frame)
        self.draw_particles()

    def draw_particles(self):
        if not self.settings.get("animations", 1) or self.settings.get("ascii", 0):
            return
        L = self.layout
        s = self.screen
        name = self._bg_name
        if name == "snow":
            for i in range(42):
                x = int((i * 37 + self.t * (7 + (i % 4) * 3)) % self.cols)
                y = int((i * 23 + self.t * (10 + (i % 5) * 4)) % (L.box_top))
                ch = "·" if i % 3 else "*"
                s.put(x, y, ch, rgb(206, 214, 226))
        elif name in ("cell", "office", "house"):
            for i in range(9):
                x = int((i * 41 + self.t * (2 + i % 3)) % self.cols)
                y = int((i * 17 + self.t * (1 + i % 2)) % (L.box_top))
                s.put(x, y, "·", rgb(120, 110, 96))

    def draw_box(self, accent=None, hints=None):
        L = self.layout
        s = self.screen
        top = L.box_top
        bottom = self.rows - 1
        s.panel(L.x0, top, L.x1, bottom, PANEL_TINT, 0.88, BOX, GOLD_DIM)
        acc = accent or GOLD
        r = self.runner
        node = r.node() if r else {}
        who = r.speaker if r else None
        name = SPEAKERS.get(who, who or "") if who is not None else ""
        if name:
            name = name.replace("{name}", r.name if r else "")
            plate = "┤ " + name + " ├"
            px = L.x0 + 3
            s.text(px, top, plate, acc)
        if r is not None:
            chapter = r.chapter
            if chapter:
                s.text(L.x1 - len(chapter) - 3, top, "─ " + chapter + " ─", GOLD_DIM)
        lines = self.uipages[min(self.uipage, len(self.uipages) - 1)] if self.uipages else []
        shown = int(self.type_i)
        remaining = shown
        text_col = SPEAKER_COLORS.get(who, PARCH)
        for i, line in enumerate(lines[: L.text_lines]):
            if remaining <= 0:
                break
            part = line[:remaining]
            s.text(L.text_x, top + 1 + i, part, text_col)
            remaining -= len(line)
        if not self.type_finished():
            if int(self.t * 2.2) % 2 == 0:
                cx = L.text_x
                cy = top + 1
                acc2 = 0
                for i, line in enumerate(lines[: L.text_lines]):
                    if acc2 + len(line) >= int(self.type_i):
                        cx = L.text_x + int(self.type_i) - acc2
                        cy = top + 1 + i
                        break
                    acc2 += len(line)
                s.put(cx, cy, "▌", acc)
        if hints:
            hint = hints
        elif self.type_finished() and self.uipage + 1 >= len(self.uipages):
            if self.runner and self.runner.current_choices():
                hint = "↑↓ выбор · ENTER"
            elif self.runner and self.runner.ending:
                hint = "ENTER · финал"
            else:
                hint = "ПРОБЕЛ ›"
        else:
            hint = "ПРОБЕЛ ›"
        if hint:
            s.text(max(L.x0 + 2, L.x1 - len(hint) - 2), bottom, hint, GOLD_DIM)
        if self.timer_t is not None and r and r.current_choices() and self.type_finished():
            total = max(0.1, self.timer_total)
            k = max(0.0, min(1.0, self.timer_t / total))
            cells = 18
            fill = int(cells * k)
            bar = "█" * fill + "░" * (cells - fill)
            col = RED if self.timer_t < 3 else GOLD
            y = top + L.text_lines + 1
            s.text(L.x1 - cells - 5, y, bar, col)
            self.draw_choices()
        elif r and r.current_choices() and self.type_finished() and self.uipage + 1 >= len(self.uipages):
            self.draw_choices()
        self.draw_toasts()

    def draw_choices(self):
        L = self.layout
        s = self.screen
        r = self.runner
        choices = r.current_choices()
        y0 = L.box_top + L.text_lines + 2
        inner = L.box_w - 8
        for i, ch in enumerate(choices[:3]):
            y = y0 + i
            text = clips(r.fmt(ch.get("text", "")), inner)
            enabled = r.choice_enabled(ch)
            selected = i == self.sel
            if selected:
                s.fill(L.x0 + 2, y, L.x1 - 2, y, " ", WHITE, rgb(54, 18, 20))
                marker = "›"
                col = GOLD_PALE if enabled else ASH
            else:
                marker = "·"
                col = PARCH if enabled else ASH
            s.text(L.x0 + 3, y, marker, RED if selected else GOLD_DIM)
            s.text(L.x0 + 5, y, text, col)
            if not enabled:
                s.text(L.x1 - 16, y, "недоступно", ASH)

    def draw_toasts(self):
        if not self.toasts:
            return
        s = self.screen
        y = 1
        for ts in self.toasts[-3:]:
            a = 1.0 - ts["t"] / ts["dur"]
            text = ts["text"]
            col = mix_int(INK, ts["col"], max(0.0, min(1.0, a)))
            x = self.cols - len(text) - 4
            if x > 4 and y < self.layout.box_top:
                s.text(x, y, text, col)
                y += 1

    def draw_chapter_label(self):
        if not self.runner or not self.runner.chapter:
            return
        label = self.runner.chapter
        self.screen.text(2, 0, " " + label + " ", GOLD_DIM, rgb(14, 12, 13))

    def draw_game(self):
        s = self.screen
        s.clear()
        self.draw_art_layer()
        self.draw_chapter_label()
        self.draw_box()
        if self.card:
            self.draw_card()

    def draw_card(self):
        if not self.card:
            return
        s = self.screen
        L = self.layout
        age = self.card_t
        if age > 3.4:
            self.card = None
            return
        alpha = min(1.0, age / 0.4)
        if age > 2.9:
            alpha = max(0.0, 1.0 - (age - 2.9) / 0.5)
        s.panel(0, 0, self.cols - 1, self.rows - 1, rgb(6, 5, 6), 0.95 * alpha)
        cy = self.rows // 2 - 3
        num = self.card.get("num", "")
        title = self.card.get("title", "")
        sub = self.card.get("subtitle", "")
        if num:
            s.text((self.cols - len(num)) // 2, cy - 3, num, GOLD_DIM)
        s.text((self.cols - len(title)) // 2, cy, title, GOLD_PALE)
        w = min(self.cols - 8, max(18, len(title) + 8))
        x0 = (self.cols - w) // 2
        s.text(x0, cy + 1, "─" * w, RED_SOFT)
        if sub:
            s.text((self.cols - len(sub)) // 2, cy + 3, sub, PARCH_DIM)
        if age > 0.5:
            hint = "ПРОБЕЛ ›"
            s.text((self.cols - len(hint)) // 2, cy + 6, hint, GOLD_DIM)

    def draw_title(self):
        s = self.screen
        self._bg_name = "title"
        grain = 0.008 if self.settings.get("grain", 1) else 0.0
        s.cells = list(self.bg_cells("title", 0.58, grain, 7))
        if self.settings.get("animations", 1):
            for k in range(10):
                idx = int((self.t * 97 + k * 613) % (self.cols * self.rows))
                ch, fg, bg = s.cells[idx]
                f = 0.90 + 0.08 * ((k * 37 + self.frame) % 3)
                s.cells[idx] = (ch, scale_int(fg, f), scale_int(bg, f))
        if self.rows >= 38:
            ly = 6
        elif self.rows >= 34:
            ly = 3
        else:
            ly = 1
        scale = 2 if self.rows >= 34 else 1
        logo_h = 7 * scale
        self.draw_logo(ly, scale)
        sub = "П А Р Т И Т У Р А"
        sub_y = ly + logo_h + 4
        s.text((self.cols - len(sub)) // 2, sub_y, sub, GOLD)
        rule_w = 36
        s.text((self.cols - rule_w) // 2, sub_y + 1, "─" * rule_w, RED_SOFT)
        items = self.title_items()
        my = sub_y + 4
        mw = min(56, self.cols - 12)
        mx = (self.cols - mw) // 2
        mh = len(items) + 2
        s.panel(mx, my - 1, mx + mw - 1, my - 1 + mh - 1, rgb(8, 7, 8), 0.62)
        for i, (key, label) in enumerate(items):
            sel = i == self.menu_sel
            disabled = key == "continue" and savemod.latest_slot() is None
            col = GOLD_PALE if sel else (ASH if disabled else PARCH_DIM)
            x = (self.cols - len(label)) // 2
            if sel:
                s.text(x - 3, my + i, "›", RED)
                s.text(x, my + i, label, col)
                s.text(x + len(label) + 1, my + i, "‹", RED)
            else:
                s.text(x, my + i, label, col if not disabled else ASH)
        foot = "фан-работа · 18+ · процедурная графика и звук"
        s.text((self.cols - len(foot)) // 2, self.rows - 1, foot, rgb(96, 88, 80))
        self.draw_toasts()

    def draw_logo(self, y, scale=2):
        s = self.screen
        text = "HANNIBAL"
        cw = 5 * scale + scale
        total = len(text) * cw - scale
        x = (self.cols - total) // 2
        flicker = 1.0
        if self.settings.get("animations", 1) and (self.frame % 240) < 3:
            flicker = 0.6
        for ci, ch in enumerate(text):
            glyph = BIG_FONT.get(ch, BIG_FONT[" "])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit != "1":
                        continue
                    px = x + ci * cw + gx * scale
                    py = y + gy * scale
                    for dy in range(scale):
                        for dx in range(scale):
                            col = GOLD_PALE if (gx + gy) % 5 else GOLD
                            col = scale_int(col, flicker * (0.9 + 0.1 * math.sin(self.t * 2 + ci)))
                            s.put(px + dx, py + dy, "█", col, rgb(8, 7, 8))
        s.text(x, y + 7 * scale + 1, "─" * total, RED)

    def draw_disclaimer(self):
        s = self.screen
        L = self.layout
        s.cells = list(self.bg_cells("cell", 0.35, 0.005, 3))
        w = min(84, self.cols - 6)
        h = min(24, self.rows - 4)
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(10, 9, 10), 0.93, BOX2, GOLD_DIM)
        title = "ПРЕДУПРЕЖДЕНИЕ О СОДЕРЖАНИИ"
        s.text(x0 + (w - len(title)) // 2, y0 + 2, title, RED)
        paragraphs = [
            "18+. Психологический триллер с элементами эротического напряжения.",
            "Насилие, манипуляции, темы каннибализма — без графических сцен.",
            "",
            "Это некоммерческая фан-работа по мотивам сериала «Ганнибал».",
            "Персонажи принадлежат их правообладателям; игра с ними не связана.",
            "",
            "Все изображения и звуки сгенерированы кодом.",
        ]
        body = []
        for p in paragraphs:
            if not p:
                body.append("")
                continue
            body.extend(wrap(p, w - 6))
        body = body[: max(0, h - 9)]
        y = y0 + 5
        for line in body:
            if line:
                s.text(x0 + 3, y, line, PARCH_DIM)
            y += 1
        hint = "ENTER — ВОЙТИ"
        s.text(x0 + (w - len(hint)) // 2, y0 + h - 3, hint, GOLD)
        s.text(x0 + (w - len("СЕРИАЛ · MADS MIKKELSEN · FAN WORK")) // 2, y0 + h - 2, "СЕРИАЛ · MADS MIKKELSEN · FAN WORK", rgb(96, 88, 80))

    def draw_name(self):
        s = self.screen
        L = self.layout
        s.cells = list(self.bg_cells("office", 0.7, 0.005, 5))
        w = min(70, self.cols - 8)
        h = 13
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, PANEL_TINT, 0.92, BOX, GOLD_DIM)
        s.text(x0 + (w - len("КАК ВАС ЗОВУТ?")) // 2, y0 + 2, "КАК ВАС ЗОВУТ?", GOLD)
        prompt = "Профайлер. Имя, которое он произнесёт вслух."
        s.text(x0 + 3, y0 + 4, prompt, PARCH_DIM)
        val = self.name_input
        caret = "▌" if (int(self.t * 2.4) % 2 == 0) else " "
        field_w = w - 8
        s.text(x0 + 3, y0 + 7, "› " + val + caret, WHITE)
        s.text(x0 + 3, y0 + 7 + 1, "─" * field_w, GOLD_DIM)
        hint = "ENTER — начать · ESC — назад"
        s.text(x0 + (w - len(hint)) // 2, y0 + h - 2, hint, GOLD_DIM)
        default_hint = "пусто — Вера"
        s.text(x0 + (w - len(default_hint)) // 2, y0 + h - 3, default_hint, rgb(96, 88, 80))

    def draw_about(self):
        s = self.screen
        L = self.layout
        s.cells = list(self.bg_cells("memory", 0.25, 0.005, 7))
        w = min(88, self.cols - 6)
        h = min(26, self.rows - 4)
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(10, 9, 10), 0.94, BOX, GOLD_DIM)
        s.text(x0 + (w - len("ОБ ИГРЕ")) // 2, y0 + 2, "ОБ ИГРЕ", GOLD)
        lines = [
            "«Ганнибал. Партитура» — консольная визуальная новелла.",
            "Фан-работа, не связанная с NBC, Томасом Харрисом и правообладателями.",
            "",
            "Код, пиксель-арт и звук генерируются процедурно во время игры.",
            "Текст и сюжет оригинальные. Совпадения случайны.",
            "",
            "УПРАВЛЕНИЕ",
            "ПРОБЕЛ / ENTER — далее     ↑ ↓ — выбор",
            "TAB — история              ESC — меню",
            "В меню сохранений: D — удалить слот",
            "",
            "Спасибо, что играете. Он уже ждёт.",
        ]
        y = y0 + 4
        for line in lines[: max(0, h - 6)]:
            col = GOLD_DIM if line.isupper() and len(line) > 3 else PARCH_DIM
            if line:
                s.text(x0 + 3, y, line, col)
            y += 1
        s.text(x0 + (w - len("ESC — НАЗАД")) // 2, y0 + h - 2, "ESC — НАЗАД", GOLD)

    def draw_pause(self):
        self.draw_game()
        s = self.screen
        s.panel(0, 0, self.cols - 1, self.rows - 1, rgb(5, 4, 5), 0.72)
        items = self.pause_items()
        w = 46
        h = len(items) + 11
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(10, 9, 10), 0.95, BOX, GOLD_DIM)
        s.text(x0 + (w - len("ПАУЗА")) // 2, y0 + 2, "ПАУЗА", GOLD)
        for i, (key, label) in enumerate(items):
            sel = i == self.sel
            col = GOLD_PALE if sel else PARCH_DIM
            x = x0 + 6
            if sel:
                s.text(x - 2, y0 + 4 + i, "›", RED)
            s.text(x, y0 + 4 + i, label, col)
        if self.runner:
            st = self.runner.stats
            y = y0 + 4 + len(items) + 1
            s.text(x0 + 4, y - 1, "─" * (w - 8), GOLD_DIM)
            s.text(x0 + 6, y, "доверие " + self.bar(st["trust"], 8), rgb(150, 178, 150))
            s.text(x0 + 6, y + 1, "желание " + self.bar(st["desire"], 8), rgb(198, 120, 118))
            s.text(x0 + 6, y + 2, "подозрение " + self.bar(st["suspicion"], 8), rgb(170, 160, 120))

    def bar(self, value, n=8):
        v = max(0, min(n, int(value * n / 10)))
        return "█" * v + "░" * (n - v)

    def draw_history(self):
        self.draw_game()
        s = self.screen
        s.panel(0, 0, self.cols - 1, self.rows - 1, rgb(5, 4, 5), 0.9)
        lines = self.history_lines()
        visible = self.rows - 5
        start = max(0, min(self.scroll, max(0, len(lines) - visible)))
        s.text(4, 1, "ИСТОРИЯ", GOLD)
        s.text(self.cols - 24, 1, "↑↓ / PgUp / PgDn", GOLD_DIM)
        for i in range(visible):
            idx = start + i
            if idx >= len(lines):
                break
            line = lines[idx]
            col = PARCH_DIM
            if line and not line.startswith(" ") and ":" in line[:20]:
                col = PARCH
            if line.startswith("›"):
                col = GOLD_PALE
            s.text(4, 3 + i, line[: self.cols - 8], col)
        s.text(4, self.rows - 1, "TAB / ESC — закрыть", GOLD_DIM)

    def draw_saves(self):
        if self.runner and self.prev_mode in ("game", "pause"):
            self.draw_game()
        else:
            self.draw_title()
        s = self.screen
        s.panel(0, 0, self.cols - 1, self.rows - 1, rgb(5, 4, 5), 0.84)
        w = min(88, self.cols - 6)
        h = 16
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        title = "СОХРАНИТЬ" if self.slot_mode == "save" else "ЗАГРУЗИТЬ"
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(10, 9, 10), 0.96, BOX, GOLD_DIM)
        s.text(x0 + (w - len(title)) // 2, y0 + 2, title, GOLD)
        slots = self.slot_list()
        for i, slot in enumerate(slots):
            y = y0 + 5 + i * 2
            info = savemod.slot_info(slot)
            sel = i == self.slot_sel
            label = "АВТО" if slot == "auto" else "СЛОТ " + slot
            if info:
                nm = info["name"]
                ch = info["chapter"] or "—"
                mins = int(info["playtime"] // 60)
                secs = int(info["playtime"] % 60)
                desc = f"{nm} · {ch} · {mins:02d}:{secs:02d}"
            else:
                desc = "пусто"
            if sel:
                s.fill(x0 + 2, y - 1, x0 + w - 2, y + 1, " ", WHITE, rgb(50, 16, 18))
            s.text(x0 + 4, y, label, GOLD_PALE if sel else PARCH_DIM)
            s.text(x0 + 16, y, desc[: w - 22], PARCH if info else ASH)
            if sel and self.slot_mode == "save" and slot == "auto":
                s.text(x0 + w - 16, y, "автосейв", ASH)
        hint = "ENTER — выбрать · D — удалить · ESC — назад"
        s.text(x0 + (w - len(hint)) // 2, y0 + h - 2, hint, GOLD_DIM)

    def draw_settings(self):
        if self.runner and self.prev_mode in ("game", "pause"):
            self.draw_game()
        else:
            self.draw_title()
        s = self.screen
        s.panel(0, 0, self.cols - 1, self.rows - 1, rgb(5, 4, 5), 0.86)
        rows = self.settings_rows()
        w = min(72, self.cols - 6)
        h = len(rows) + 8
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(10, 9, 10), 0.96, BOX, GOLD_DIM)
        s.text(x0 + (w - len("НАСТРОЙКИ")) // 2, y0 + 2, "НАСТРОЙКИ", GOLD)
        for i, (key, label, value) in enumerate(rows):
            y = y0 + 4 + i
            sel = i == self.settings_sel
            col = GOLD_PALE if sel else PARCH_DIM
            if sel:
                s.text(x0 + 4, y, "›", RED)
            s.text(x0 + 6, y, label, col)
            s.text(x0 + w - len(value) - 8, y, "‹ " + value + " ›", GOLD if sel else PARCH_DIM)
        hint = "↑↓ · ←→ изменить · ESC — назад"
        s.text(x0 + (w - len(hint)) // 2, y0 + h - 2, hint, GOLD_DIM)

    def draw_ending(self):
        s = self.screen
        L = self.layout
        r = self.runner
        end = STORY.ENDINGS.get(r.ending, {}) if r else {}
        bgname = end.get("bg", "snow")
        grain = 0.01 if self.settings.get("grain", 1) else 0.0
        s.cells = list(self.bg_cells(bgname, 0.45, grain, 11))
        w = min(86, self.cols - 6)
        h = min(22, self.rows - 4)
        x0 = (self.cols - w) // 2
        y0 = (self.rows - h) // 2
        s.panel(x0, y0, x0 + w - 1, y0 + h - 1, rgb(8, 7, 8), 0.93, BOX2, GOLD_DIM)
        title = end.get("title", "КОНЕЦ")
        sub = end.get("subtitle", "")
        s.text(x0 + (w - len(title)) // 2, y0 + 3, title, GOLD_PALE)
        s.text(x0 + (w - len(sub)) // 2, y0 + 5, sub, RED)
        s.text(x0 + 3, y0 + 8, "─" * (w - 6), GOLD_DIM)
        lines = wrap(end.get("text", ""), w - 8)
        y = y0 + 10
        for line in lines[: h - 14]:
            s.text(x0 + 4, y, line, PARCH_DIM)
            y += 1
        if r:
            y = y0 + h - 5
            s.text(x0 + 4, y, "доверие " + self.bar(r.stats["trust"], 8), rgb(150, 178, 150))
            s.text(x0 + 4, y + 1, "желание " + self.bar(r.stats["desire"], 8), rgb(198, 120, 118))
            s.text(x0 + 4, y + 2, "подозрение " + self.bar(r.stats["suspicion"], 8), rgb(170, 160, 120))
        hint = "ENTER — в главное меню"
        s.text(x0 + (w - len(hint)) // 2, y0 + h - 2, hint, GOLD)
        self.draw_toasts()
