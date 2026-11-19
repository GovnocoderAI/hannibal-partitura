import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from engine.game import Game

PICKS = {"p_3": 1, "p_4": 0, "p_6": 0, "p_8": 0, "p_9": 0, "c1_2": 1, "c1_4": 0,
         "c1_6": 1, "c1_7": 1, "c1_9": 2, "c2_3": 2, "c2_4": 0, "c2_6": 1,
         "c2_7": 0, "c2_8": 0, "c2_10": 2, "c3_1": 1, "c3_3": 1, "c3_6": 1, "c3_8": 0}


OUT = []


def dump(g, label):
    if g.card is not None:
        g.card = None
        g.draw()
    OUT.append("=" * 20 + " " + label + " " + "=" * 20)
    for y in range(g.screen.rows):
        line = []
        for x in range(g.screen.cols):
            ch = g.screen.cells[y * g.screen.cols + x][0]
            line.append(ch if ch != "в–Ђ" else "в–€")
        OUT.append("".join(line).rstrip())
    OUT.append("")


def play_to(g, target):
    for i in range(1500):
        if g.runner is None or g.runner.node_id == target:
            break
        if g.mode != "game":
            break
        render = False
        if g.runner.current_choices():
            if not g.type_finished():
                g.step([], render=render)
                continue
            if g.uipage + 1 < len(g.uipages):
                g.step(["SPACE"], render=render)
                continue
            idx = PICKS.get(g.runner.node_id, 0)
            ch = g.runner.current_choices()
            if idx >= len(ch) or not g.runner.choice_enabled(ch[idx]):
                idx = 0
            g.sel = idx
            if g.choice_shown_t >= 0 and g.t - g.choice_shown_t < 0.12:
                g.step([], render=render)
                continue
            g.step(["ENTER"], render=render)
        else:
            g.step(["SPACE"], render=render)
    while not g.type_finished():
        g.step([], render=False)
    g.draw()
    return g


g = Game(headless=True, width=120, height=40)
g.settings["text_speed"] = 3
g.settings["sound"] = 0
g.set_mode("disclaimer")
g.draw()
dump(g, "disclaimer")
g.set_mode("title")
g.draw()
dump(g, "title")
g.set_mode("name")
g.draw()
dump(g, "name")
g.set_mode("about")
g.draw()
dump(g, "about")
g.set_mode("settings")
g.draw()
dump(g, "settings")

g.set_mode("disclaimer")
g.step(["ENTER"])
g.step(["ENTER"])
for ch in "Р’РµСЂР°":
    g.step([ch])
g.step(["ENTER"])
play_to(g, "p_6")
dump(g, "game p_6 timer")
play_to(g, "c2_2")
dump(g, "game c2_2")
play_to(g, "c2_8")
dump(g, "game c2_8 choices")
g.set_mode("pause")
g.draw()
dump(g, "pause")
g.set_mode("history")
g.draw()
dump(g, "history")
g.set_mode("saves")
g.slot_mode = "save"
g.draw()
dump(g, "saves")
play_to(g, "c3_8")
g.set_mode("saves")
g.slot_mode = "load"
g.draw()
dump(g, "saves load")
g.set_mode("game")
play_to(g, "end_partitura_c")
g.step(["SPACE"])
g.draw()
dump(g, "ending")

with open(os.path.join(ROOT, 'preview', 'screens.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(OUT))
print('ok')

