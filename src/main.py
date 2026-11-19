import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import save as savemod


def crash_path():
    return os.path.join(savemod.APP_DIR, "crash.log")


def write_crash(text):
    try:
        savemod.ensure_dirs()
        with open(crash_path(), "a", encoding="utf-8") as f:
            f.write("\n--- " + time.strftime("%Y-%m-%d %H:%M:%S") + " ---\n")
            f.write(text)
    except Exception:
        pass


def run_game():
    from engine.game import Game

    game = None
    try:
        game = Game()
        game.start()
    except KeyboardInterrupt:
        pass
    except Exception:
        write_crash(traceback.format_exc())
        try:
            if game is not None:
                game.console.restore()
        except Exception:
            pass
        print("Произошла ошибка. Лог сохранён в:", crash_path())
        print(traceback.format_exc())
        try:
            input("Нажмите Enter, чтобы закрыть...")
        except Exception:
            pass


def export_art(outdir=None):
    from art.faces import get_portrait, EXPRESSIONS
    from art.scenes_art import get_bg
    from art.canvas import Canvas

    root = os.path.dirname(HERE)
    out = outdir or os.path.join(root, "preview")
    os.makedirs(out, exist_ok=True)

    def backdrop():
        c = Canvas(120, 80)
        c.vertical_gradient(0, 80, (16, 14, 16), (8, 7, 9))
        c.radial(34, 22, 58, (70, 46, 26), 0.28, 2.0)
        return c

    names = {
        "hannibal": ["neutral", "warm", "amused", "predatory", "cold", "intimate", "closed", "hungry", "bloody", "smile_talk"],
        "rurke": ["neutral", "cold"],
        "chilton": ["neutral", "amused"],
        "composer": ["neutral", "predatory"],
        "heroine": ["neutral", "intimate"],
    }
    for name, exprs in names.items():
        p = get_portrait(name)
        for expr in exprs:
            if expr not in EXPRESSIONS:
                continue
            img = backdrop()
            img.composite(p.frame(expr))
            img.vignette(0.35, 2.0)
            img.save_png(os.path.join(out, f"{name}_{expr}.png"), scale=4, levels=24, dither=0.6)
    for bg in ("cell", "corridor", "office", "dinner", "snow", "house", "memory", "title"):
        get_bg(bg).save_png(os.path.join(out, "bg_" + bg + ".png"), scale=4, levels=24, dither=0.5)
    print("Экспорт готов:", out)


def run_smoke():
    from engine.game import Game

    g = Game()
    g.console.setup()
    try:
        g.set_mode("title")
        for _ in range(24):
            g.step([], dt=1.0 / 30.0, render=True)
            g.screen.present(g.console)
            time.sleep(0.02)
        g.audio.play_ambient("cell")
        time.sleep(1.4)
        g.audio.sfx("clink")
        time.sleep(0.2)
    finally:
        try:
            g.audio.shutdown()
        except Exception:
            pass
        g.console.restore()
    print("SMOKE OK")


def run_selftest():
    from story.validate import validate
    from story.content import NODES, START
    from engine.story_runner import Runner

    errors = validate()
    if errors:
        print("ОШИБКИ СЮЖЕТА:")
        for e in errors:
            print(" -", e)
    else:
        print("Сюжет: OK, нод:", len(NODES))

    routes = {
        "partitura": ["p_3:1", "p_4:0", "p_6:0", "p_8:0", "p_9:0", "c1_2:1", "c1_4:0",
                      "c1_6:1", "c1_7:1", "c1_9:2", "c2_3:2", "c2_4:0", "c2_6:1",
                      "c2_7:0", "c2_8:0", "c2_10:2", "c3_1:1", "c3_3:1", "c3_6:1", "c3_8:0"],
        "cadence": ["p_3:0", "p_4:0", "p_6:1", "p_8:1", "p_9:1", "c1_2:0", "c1_4:1",
                    "c1_6:0", "c1_7:0", "c1_9:1", "c2_3:0", "c2_4:2", "c2_6:0",
                    "c2_7:1", "c2_8:1", "c2_10:1", "c3_1:0", "c3_3:2", "c3_6:0", "c3_8:1"],
        "silence": ["p_3:2", "p_4:1", "p_6:1", "p_8:1", "p_9:1", "c1_2:0", "c1_4:1",
                    "c1_6:2", "c1_7:0", "c1_9:0", "c2_3:1", "c2_4:1", "c2_6:1",
                    "c2_7:1", "c2_8:2", "c2_10:0"],
    }
    for name, route in routes.items():
        picks = {k: int(v) for k, v in (x.split(":") for x in route)}
        r = Runner(NODES, START)
        steps = 0
        while r.ending is None and steps < 400:
            steps += 1
            if r.current_choices():
                idx = picks.get(r.node_id, 0)
                choices = r.current_choices()
                if idx >= len(choices):
                    idx = 0
                if not r.choice_enabled(choices[idx]):
                    for j in range(len(choices)):
                        if r.choice_enabled(choices[j]):
                            idx = j
                            break
                r.choose(idx)
            else:
                if not r.advance():
                    break
        print(f"Маршрут {name}: {r.node_id} -> {r.ending} (шагов {steps})")

    from engine.game import Game

    for name in routes:
        g = Game(headless=True, width=120, height=40)
        g.settings["text_speed"] = 3
        g.settings["sound"] = 0
        g.settings["animations"] = 1
        g.step(["ENTER"])
        g.step(["ENTER"])
        for ch in "Тест":
            g.step([ch])
        g.step(["ENTER"])
        picks = {k: int(v) for k, v in (x.split(":") for x in routes[name])}
        for i in range(1500):
            if g.mode == "ending":
                break
            if g.mode != "game" or g.runner is None:
                break
            render = (i % 25 == 0)
            if g.runner.current_choices():
                if not g.type_finished():
                    g.step([], render=render)
                    continue
                if g.uipage + 1 < len(g.uipages):
                    g.step(["SPACE"], render=render)
                    continue
                node = g.runner.node_id
                idx = picks.get(node, 0)
                choices = g.runner.current_choices()
                if idx >= len(choices) or not g.runner.choice_enabled(choices[idx]):
                    idx = 0
                    for j in range(len(choices)):
                        if g.runner.choice_enabled(choices[j]):
                            idx = j
                            break
                g.sel = idx
                if g.choice_shown_t >= 0 and g.t - g.choice_shown_t < 0.12:
                    g.step([], render=render)
                    continue
                g.step(["ENTER"], render=render)
            else:
                g.step(["SPACE"], render=render)
        print(f"UI {name}: mode={g.mode} ending={g.runner.ending if g.runner else None}")

    g = Game(headless=True, width=120, height=40)
    for mode in ("disclaimer", "title", "name", "about"):
        g.set_mode(mode)
        g.draw()
    print("UI-экраны: OK")


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    args = sys.argv[1:]
    if "--version" in args:
        print("HannibalVN 1.0")
        return
    if "--export-art" in args:
        i = args.index("--export-art")
        outdir = args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith("--") else None
        export_art(outdir)
        return
    if "--selftest" in args:
        run_selftest()
        return
    if "--smoke" in args:
        run_smoke()
        return
    run_game()


if __name__ == "__main__":
    main()
