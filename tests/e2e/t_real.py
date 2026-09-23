"""Final real-input (SendInput) suite against the INSTALLED extension, on the
125% monitor. Runs only while the human is idle; retries touched gestures.
Includes the user's success criterion: ~600x337 full frame -> ~480x337 showing
the central 1536x1080 of the source (10% cut left and right)."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip, winutil as W

LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


t = pip.T()
t.chrome("PC._setNativeForTests(null); return PC.native;")      # real GetAsyncKeyState/GetCursorPos
t.close_all()
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4")
time.sleep(1.5)
log("waiting for the user to be idle >= 20 s ...")
W.wait_idle(20000, timeout=6 * 3600)
pid = t.open_pip(wait=0.8)
t.player_call(pid, "setRect", {"x": 60, "y": 470, "w": 600, "h": 338})
time.sleep(3)


def st():
    return [x for x in t.pips() if x["id"] == pid][0]["crop"]


def rect4(s):
    r = s["rect"]
    return (r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])


def snap(label):
    t.wait_controls_hidden()
    s = st()
    v = pip.shot(f"90_real_{label}", rect=rect4(s), crop=s["crop"])[0].get("verify")
    c = s["crop"]
    r = s["rect"]
    if v:
        log(f"{label:24s} window {r['w']}x{r['h']}@{r['x']},{r['y']} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} "
            f"| source shown x {v['x'].get('src0')}..{v['x'].get('src1')} y {v['y'].get('src0')}..{v['y'].get('src1')} "
            f"| grid {v['x']['matched']}/{v['x']['expected_lines']}+{v['y']['matched']}/{v['y']['expected_lines']} rms {v['x']['rms_px']}/{v['y']['rms_px']} "
            f"| scale {v['x'].get('scale')}/{v['y'].get('scale')} stretch {v.get('stretch')} | black {sum(v['black_px'].values())} darkEdges {v['edges_dark']}")
    return s


def point(r, where, inset=7):
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    return {"l": (x + inset, y + h // 2), "r": (x + w - 1 - inset, y + h // 2), "t": (x + w // 2, y + inset),
            "b": (x + w // 2, y + h - 1 - inset), "br": (x + w - 1 - inset, y + h - 1 - inset), "c": (x + w // 2, y + h // 3)}[where]


def real(label, where, dx, dy, shift):
    for attempt in range(12):
        W.wait_idle(5000, timeout=6 * 3600)
        before = st()
        x0, y0 = point(before["rect"], where)
        touched = W.drag(x0, y0, x0 + dx, y0 + dy, steps=22, step_ms=14, shift=shift)
        time.sleep(0.9)
        if not touched:
            return snap(label)
        log(f"   ({label}: human input overlapped; restoring and retrying)")
        t.player_call(pid, "setRect", before["rect"])
        t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
          const p=PC.player(w); p.crop = arguments[1]; p.applySteadyLayout(); return 1;""", pid, before["crop"])
        time.sleep(1)
    raise RuntimeError("no idle window")


base = snap("A_before_600x338")
real("B_shift_left_in_60", "l", +60, 0, True)
after = real("C_shift_right_in_60", "r", -60, 0, True)
real("D_shift_top_in_34", "t", 0, +34, True)
real("E_shift_bottom_in_34", "b", 0, -34, True)
real("F_shift_left_out_30", "l", -30, 0, True)
real("G_plain_corner_grow", "br", +48, +27, False)
real("H_plain_move", "c", -40, -30, False)
# Shift + double-click resets the crop
W.wait_idle(5000, timeout=6 * 3600)
s = st()
cx, cy = point(s["rect"], "c")
old = W.cursor_pos()
W.key(W.VK_LSHIFT, True); time.sleep(0.05)
W.mouse_move(cx, cy); time.sleep(0.08)
for _ in range(2):
    W.mouse_button(True); time.sleep(0.03); W.mouse_button(False); time.sleep(0.06)
W.key(W.VK_LSHIFT, False); W.mouse_move(*old)
time.sleep(1.0)
snap("I_shift_dblclick_reset")
json.dump(LOG, open(os.path.join(pip.OUT, "real_run.json"), "w"), indent=1)
t.close_all()
t.close()
log("REAL-INPUT SUITE DONE")
