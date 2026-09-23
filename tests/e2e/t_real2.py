"""v1.1 real-input checks on Windows' own sizing loop: outward crop drags stop
at the video edge (captured while the button is still down), and releasing the
button while the mouse is still moving leaves no stretch."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import ctypes, json, time
import piptest as pip, winutil as W

t = pip.T()
t.chrome("PC._setNativeForTests(null); return PC.native;")
t.close_all()
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8)
t.player_call(pid, "setRect", {"x": 60, "y": 520, "w": 480, "h": 270})
time.sleep(2.5)
RESULTS = []


def st():
    found = [x for x in t.pips() if x["id"] == pid]
    if not found:
        raise RuntimeError("the test PiP window was closed")
    return found[0]["crop"]


def rect4(r):
    return (r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])


def verify(label, s=None, win_rect=None):
    s = s or st()
    r = win_rect or s["rect"]
    sh = pip.shot(f"96_{label}", rect=rect4(r), crop=s["crop"])[0]
    if sh.get("missing") or sh.get("occluded"):
        return {"label": label, "capture": "skipped (PiP not visible there)"}
    v = sh["verify"]
    c = s["crop"]
    out = {"label": label, "rect": r, "crop": {k: round(x, 3) for k, x in c.items()},
           "grid": f"{v['x']['matched']}/{v['x']['expected_lines']}+{v['y']['matched']}/{v['y']['expected_lines']}",
           "scale": [v["x"].get("scale"), v["y"].get("scale")], "black": sum(v["black_px"].values()),
           "darkEdges": v["edges_dark"]}
    return out


def point(r, where, inset=7):
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    return {"l": (x + inset, y + h // 2), "r": (x + w - 1 - inset, y + h // 2),
            "t": (x + w // 2, y + inset), "br": (x + w - 1 - inset, y + h - 1 - inset)}[where]


def hold_drag(label, where, dx, dy, shift=True, capture=True):
    """Press, move, capture while still holding, release. Retries if a human
    moved the mouse meanwhile."""
    for attempt in range(10):
        W.wait_idle(5000, timeout=6 * 3600)
        before = st()
        x0, y0 = point(before["rect"], where)
        old = W.cursor_pos()
        foreign = False
        try:
            if shift:
                W.key(W.VK_LSHIFT, True)
            W.mouse_move(x0, y0); time.sleep(0.25)          # hover: lets the player arm the edge
            armed = st()
            W.mouse_button(True); time.sleep(0.06)
            for i in range(1, 25):
                W.mouse_move(x0 + dx * i / 24, y0 + dy * i / 24)
                time.sleep(0.012)
                if W.cursor_pos() != (int(x0 + dx * i / 24), int(y0 + dy * i / 24)):
                    foreign = True
            time.sleep(0.25)
            during = st()
            real = [x["rect"] for x in W.windows() if x["cls"] == "MozillaDialogClass" and x["rect"][0] < W.primary_monitor()[2] and x["title"] == "Picture-in-Picture"]
            cap = verify(label + "_HOLDING", during) if capture else None
        finally:
            W.mouse_button(False)
            time.sleep(0.05)
            if shift:
                W.key(W.VK_LSHIFT, False)
            W.mouse_move(*old)
        time.sleep(0.8)
        if foreign:
            t.player_call(pid, "setRect", before["rect"])
            t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
              const p=PC.player(w); p.crop = arguments[1]; p.applySteadyLayout(); return 1;""", pid, before["crop"])
            time.sleep(1)
            continue
        after = verify(label + "_AFTER")
        rec = {"test": label, "before": before["rect"], "armed_before_press": armed["armed"],
               "limit_before_press": armed["constraints"], "during_rect": during["rect"], "during_os": real,
               "during_capture": cap, "after": after}
        print(json.dumps(rec), flush=True)
        RESULTS.append(rec)
        return rec
    raise RuntimeError("no idle window")


def release_while_moving(label, where, dx):
    """Moves and the button-up injected as ONE SendInput batch: Windows'
    async key state says 'up' while the loop still drains the queued moves."""
    for attempt in range(10):
        W.wait_idle(5000, timeout=6 * 3600)
        before = st()
        x0, y0 = point(before["rect"], where)
        old = W.cursor_pos()
        W.key(W.VK_LSHIFT, True)
        W.mouse_move(x0, y0); time.sleep(0.25)
        W.mouse_button(True); time.sleep(0.06)
        for i in range(1, 9):                     # a first part of the drag, paced
            W.mouse_move(x0 + dx * i / 20, y0); time.sleep(0.012)
        batch = []
        for i in range(9, 21):
            x = int(x0 + dx * i / 20)
            batch.append(("move", x, y0))
            if i == 12:
                batch.append(("up", 0, 0))
        W.send_batch(batch)                        # remaining moves + release, all queued at once
        time.sleep(0.05)
        W.key(W.VK_LSHIFT, False)
        W.mouse_move(*old)
        time.sleep(1.0)
        s = st()
        r = s["rect"]; c = s["crop"]
        fw = r["w"] / (1 - c["l"] - c["r"]); fh = r["h"] / (1 - c["t"] - c["b"])
        after = verify(label + "_AFTER", s)
        rec = {"test": label, "before": before["rect"], "after": after, "frame_aspect": round(fw / fh, 4),
               "unlocked": s["unlocked"], "constraints": s["constraints"]}
        print(json.dumps(rec), flush=True)
        RESULTS.append(rec)
        return rec
    raise RuntimeError("no idle window")


print(json.dumps({"base": verify("base")}), flush=True)
if "--from-r3" in sys.argv:
    t.player_call(pid, "setCrop", {"l": 80 / 480})      # state right after R2
    time.sleep(1.0)
    print(json.dumps({"state_after_R2": verify("after_R2_restored")}), flush=True)
else:
    hold_drag("R1_right_out_uncropped", "r", +250, 0)
    hold_drag("R2_left_in_80", "l", +80, 0, capture=False)
hold_drag("R3_left_out_250", "l", -250, 0)
hold_drag("R4a_top_in_40", "t", 0, +40, capture=False)
hold_drag("R4b_top_out_200", "t", 0, -200)
release_while_moving("R5_release_while_moving", "r", -120)
hold_drag("R6_plain_corner_grow", "br", +60, +34, shift=False, capture=False)
json.dump(RESULTS, open(os.path.join(pip.OUT, "real_run2.json"), "w"), indent=1)
t.close_all(); t.close()
print("REAL2 DONE", flush=True)
