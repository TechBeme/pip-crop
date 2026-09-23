"""End-to-end gesture tests with real OS input (SendInput) on the native PiP
border: Shift+drag = crop, plain drag = proportional resize."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip, winutil as W

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "v169.mp4"
SRC_W, SRC_H = {"v169.mp4": (1920, 1080), "v43.mp4": (1440, 1080), "vvert.mp4": (1080, 1920)}[VIDEO]
TAG = sys.argv[2] if len(sys.argv) > 2 else "g"

t = pip.T()
t.close_all()
print("install:", t.install())
t.m.navigate(f"http://127.0.0.1:8765/video.html?src={VIDEO}")
time.sleep(1.5)
pid = t.open_pip(wait=3.5)
# park the PiP in the middle of the secondary monitor so growth stays on screen
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  w.moveTo(3440 + 560, 225 + 300); await new Promise(r => setTimeout(r, 400)); return 1;""", pid)


def state():
    p = [x for x in t.pips() if x["id"] == pid][0]
    return p["crop"]


def point(rect, where, inset=6):
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    return {
        "left": (x + inset, y + h // 2), "right": (x + w - 1 - inset, y + h // 2),
        "top": (x + w // 2, y + inset), "bottom": (x + w // 2, y + h - 1 - inset),
        "topleft": (x + inset, y + inset), "bottomright": (x + w - 1 - inset, y + h - 1 - inset),
        "center": (x + w // 2, y + h // 3),
    }[where]


def gesture(name, where, dx, dy, shift, steps=24, step_ms=14):
    s0 = state()
    r0 = s0["rect"]
    x0, y0 = point(r0, where)
    hit = W.root_of(W.window_from_point(x0, y0))
    if not W.wait_idle(3000, timeout=900):
        print("user busy; skipping", name)
        return None
    W.drag(x0, y0, x0 + dx, y0 + dy, steps=steps, step_ms=step_ms, shift=shift)
    time.sleep(0.9)
    s1 = state()
    shot = pip.shot(f"40_{TAG}_{name}", SRC_W, SRC_H)
    shot = [s for s in shot if s["rect"] == (s1["rect"]["x"], s1["rect"]["y"], s1["rect"]["x"] + s1["rect"]["w"], s1["rect"]["y"] + s1["rect"]["h"])] or shot
    s = shot[0]
    c = s1["crop"]
    print(f"{name:22s} {'SHIFT' if shift else 'plain'} {where:11s} d=({dx:+d},{dy:+d}) hitPiP={bool(hit)} "
          f"rect {r0['w']}x{r0['h']}@{r0['x']},{r0['y']} -> {s1['rect']['w']}x{s1['rect']['h']}@{s1['rect']['x']},{s1['rect']['y']} "
          f"crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} | src={s['src']} sx={s['sx']} sy={s['sy']} "
          f"stretch={s['stretch']} black={s['black_px']} edges={s['edges']} offscreen={s['offscreen_px']} unlocked={s1['unlocked']}", flush=True)
    return s1, s


base = pip.shot(f"40_{TAG}_base", SRC_W, SRC_H)[0]
print("base:", json.dumps(state()), json.dumps({k: base[k] for k in ("win", "src", "sx", "sy", "black_px")}))
gesture("crop_left_in", "left", +80, 0, True)
gesture("crop_right_in", "right", -60, 0, True)
gesture("crop_top_in", "top", 0, +40, True)
gesture("crop_bottom_in", "bottom", 0, -30, True)
gesture("uncrop_left_out", "left", -40, 0, True)
gesture("overshoot_left_out", "left", -200, 0, True)
gesture("resize_plain_corner", "bottomright", +90, +50, False)
gesture("resize_plain_left", "left", -60, 0, False)
gesture("move_plain", "center", -120, -40, False)
gesture("crop_corner_topleft", "topleft", +50, +30, True)
t.close()
