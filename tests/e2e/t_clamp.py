"""v1.1: outward crop drags stop at the video edge; release during motion."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip, winutil, analyze
from sim import Sim, INSTALL_FAKE
t = pip.T()
t.close_all()
if not os.environ.get("PIPCROP_NO_INJECT"):
    t.install()
t.chrome(INSTALL_FAKE)
t.chrome('Services.prefs.setBoolPref("extensions.pipcrop.debug", true); return 1;')
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8)
sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 520, "w": 480, "h": 270})
time.sleep(2.5)
st0 = sim.state()
r0 = st0["rect"]
cal_im = winutil.grab((r0["x"], r0["y"], r0["x"] + r0["w"], r0["y"] + r0["h"]))

def check(name, st, expect=None):
    t.wait_controls_hidden()
    r = st["rect"]; c = st["crop"]
    v = pip.shot(f"95_{name}", rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=c)[0].get("verify", {})
    fw = r["w"] / (1 - c["l"] - c["r"]); fh = r["h"] / (1 - c["t"] - c["b"])
    ok = (sum(v.get("black_bands", {"x": 9}).values()) == 0 and abs(fw / fh - 16 / 9) < 0.012
          and st["constraints"] is None and not st["unlocked"] and not st["gesture"])
    if expect:
        ok = ok and all(abs(r[k] - expect[k]) <= 1 for k in expect)
    print(f"{'PASS' if ok else 'FAIL'} {name:24s} rect={r['w']}x{r['h']}@{r['x']},{r['y']} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} "
          f"frameAspect={fw/fh:.4f} | grid {v.get('x',{}).get('matched')}/{v.get('x',{}).get('expected_lines')}+{v.get('y',{}).get('matched')}/{v.get('y',{}).get('expected_lines')} "
          f"scale {v.get('x',{}).get('scale')}/{v.get('y',{}).get('scale')} bands {v.get("black_bands")} constraints={st['constraints']} unlocked={st['unlocked']}", flush=True)
    return ok

base = sim.state(); check("base", base)
R = base["rect"]
# 1. uncropped: pulling any edge outward must not grow the window at all
check("right_out_uncropped", sim.gesture("r", dx=+300), {"x": R["x"], "w": R["w"]})
check("left_out_uncropped", sim.gesture("l", dx=-300), {"x": R["x"], "w": R["w"]})
check("bottom_out_uncropped", sim.gesture("b", dy=+300), {"y": R["y"], "h": R["h"]})
check("top_out_uncropped", sim.gesture("t", dy=-300), {"y": R["y"], "h": R["h"]})
# 2. crop, then pull each edge far outward: must stop exactly at the video edge
sim.gesture("l", dx=+80); sim.gesture("r", dx=-60); sim.gesture("t", dy=+40); sim.gesture("b", dy=-30)
check("cropped_4_sides", sim.state())
check("left_out_to_edge", sim.gesture("l", dx=-400), {"x": R["x"]})
check("right_out_to_edge", sim.gesture("r", dx=+400), {"x": R["x"], "w": R["w"]})
check("top_out_to_edge", sim.gesture("t", dy=-400), {"y": R["y"]})
check("bottom_out_to_edge", sim.gesture("b", dy=+400), {"y": R["y"], "h": R["h"]})
# 3. release while still moving: queued moves after the button is up
st = sim.gesture("r", dx=-50, steps=8, trailing=5)
check("release_while_moving", st, {"w": R["w"] - round(50 * 13 / 8)})
st = sim.gesture("l", dx=+40, steps=8, trailing=5)
check("release_while_moving_L", st)
# 4. modifier pressed too late to arm (no hover): right/bottom still capped
st = sim.gesture("r", dx=+300, pre=False)
check("late_modifier_right_out", st)
print(json.dumps(t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  return PC.player(w).debugLog.filter(e => e[1] === 'begin' || e[1] === 'finish').slice(-4);""", pid))[:1500])
t.close_all(); t.close()
