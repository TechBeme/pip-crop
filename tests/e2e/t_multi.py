"""3 tabs -> 3 simultaneous native PiP windows, independent crops, controls."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip
from sim import Sim, INSTALL_FAKE

VIDEOS = [("A", "v169.mp4", 1920, 1080, {"x": 60, "y": 240, "w": 420}),
          ("B", "v43.mp4", 1440, 1080, {"x": 60, "y": 620, "w": 360}),
          ("C", "vvert.mp4", 1080, 1920, {"x": 540, "y": 240, "w": 240})]

t = pip.T()
t.close_all()
print("install:", t.install() if not os.environ.get("PIPCROP_NO_INJECT") else ("extension", t.status()))
t.chrome(INSTALL_FAKE)
tabs, pids, dims = {}, {}, {}
first = True
for name, vid, W, H, pos in VIDEOS:
    url = f"http://127.0.0.1:8765/video.html?src={vid}"
    if first:
        t.m.navigate(url)
        tabs[name] = t.m.send("WebDriver:GetWindowHandle")["value"]
        first = False
    else:
        tabs[name] = t.new_tab(url)
    time.sleep(1.5)
    pids[name] = t.open_pip(wait=0.8)
    dims[name] = (W, H)
    t.player_call(pids[name], "setRect", {**pos, "h": round(pos["w"] * H / W)})
print("pip ids:", pids, "count:", len(t.pips()))
time.sleep(2.5)


def states():
    return {n: [x for x in t.pips() if x["id"] == pids[n]][0]["crop"] for n in pids}


def verify(label):
    t.wait_controls_hidden()
    st = states()
    for n, s in st.items():
        r = s["rect"]
        W, H = dims[n]
        sh = pip.shot(f"60_{label}_{n}", W, H, rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=s["crop"])[0]
        v = sh.get("verify")
        c = s["crop"]
        if not v:
            print(f"  {n}: occluded")
            continue
        print(f"  {label:14s} {n} {r['w']}x{r['h']}@{r['x']},{r['y']} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} "
              f"| gridX {v['x']['matched']}/{v['x']['expected_lines']} rms {v['x']['rms_px']} gridY {v['y']['matched']}/{v['y']['expected_lines']} rms {v['y']['rms_px']} "
              f"scale {v['x'].get('scale')}/{v['y'].get('scale')} black {sum(v['black_px'].values())}", flush=True)
    return st


def page(name, code):
    t.m.send("WebDriver:SwitchToWindow", {"handle": tabs[name], "focus": False})
    return t.content(code)


def videos():
    return {n: page(n, "const v=document.querySelector('video'); return {paused: v.paused, t: +v.currentTime.toFixed(2)};") for n in tabs}


s0 = verify("start")
sims = {n: Sim(t, pids[n]) for n in pids}
sims["A"].gesture("l", dx=+50)
s1 = verify("A_left")
assert s1["B"]["crop"] == s0["B"]["crop"] and s1["C"]["crop"] == s0["C"]["crop"], "A's crop leaked"
sims["B"].gesture("t", dy=+40)
sims["C"].gesture("r", dx=-30)
sims["C"].gesture("b", dy=-60)
s2 = verify("B_top_C_rb")
assert s2["A"]["crop"] == s1["A"]["crop"], "B/C leaked into A"
print("videos before controls:", videos())
# play/pause through B's own PiP control, seek through C's own PiP scrubber
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  w.document.getElementById("playpause").click(); return 1;""", pids["B"])
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  const s=w.document.getElementById("scrubber"); s.value = 0.5;
  s.dispatchEvent(new w.Event("input", {bubbles: true})); s.dispatchEvent(new w.Event("change", {bubbles: true})); return 1;""", pids["C"])
time.sleep(1.2)
v1 = videos()
print("videos after B pause + C seek(50%):", v1)
time.sleep(1.0)
v2 = videos()
print("videos 1s later:", v2, "(A,C advancing; B frozen)")
s3 = verify("after_controls")
assert all(s3[n]["crop"] == s2[n]["crop"] for n in pids), "controls changed a crop"
# close B through its own close button; A and C must be untouched
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  w.document.getElementById("close").click(); return 1;""", pids["B"])
time.sleep(1.5)
left = [x["id"] for x in t.pips()]
print("pips left after closing B:", left)
del pids["B"]
s4 = verify("after_close_B")
assert all(s4[n]["crop"] == s3[n]["crop"] and s4[n]["rect"] == s3[n]["rect"] for n in pids), "closing B affected others"
print("MULTI-PIP OK")
t.close_all()
t.close()
