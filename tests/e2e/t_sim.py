"""Gesture battery with simulated input (fake modifier/button/cursor; the window
steps of a sizing loop applied with SetWindowPos) on a 16:9, 4:3 or vertical
video: crop each side, uncrop, overshoot, minimum size.

    python tests/e2e/t_sim.py [v169.mp4|v43.mp4|vvert.mp4] [position json] [tag]"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import time, json
import piptest as pip
from sim import Sim, report
VIDEO = sys.argv[1] if len(sys.argv) > 1 else "v169.mp4"
SW, SH = {"v169.mp4": (1920, 1080), "v43.mp4": (1440, 1080), "vvert.mp4": (1080, 1920)}[VIDEO]
POS = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {"x": 60, "y": 520, "w": 480}
TAG = sys.argv[3] if len(sys.argv) > 3 else "s"
t = pip.T()
t.close_all()
t.install() if not os.environ.get("PIPCROP_NO_INJECT") else print("using installed extension:", t.status())
t.m.navigate(f"http://127.0.0.1:8765/video.html?src={VIDEO}"); time.sleep(1.5)
pid = t.open_pip(wait=1.0)
sim = Sim(t, pid)
a = SW / SH
sim.player("setRect", {"x": POS["x"], "y": POS["y"], "w": POS["w"], "h": round(POS["w"] / a)})
time.sleep(2.8)   # let the initial controls fade
import analyze, winutil, os
def rect4(st): return (st['rect']['x'], st['rect']['y'], st['rect']['x'] + st['rect']['w'], st['rect']['y'] + st['rect']['h'])
st0 = sim.state()
im = winutil.grab(rect4(st0))
try:
    cal = analyze.calibrate(im, SW, SH)
except Exception:
    cal = (1.0, 0.0, 1.0, 0.0)
json.dump([float(x) for x in cal], open(os.path.join(pip.OUT, f"calib_{TAG}.json"), "w"))
print("calibration for this monitor:", [round(float(x), 3) for x in cal])
def step(name, st):
    time.sleep(0.4)
    t.wait_controls_hidden()
    report(name, st, pip.shot(f"50_{TAG}_{name}", SW, SH, calib=TAG, rect=rect4(st), crop=st["crop"]))
step("base", sim.state())
step("crop_left_in", sim.gesture("l", dx=+60))
step("crop_right_in", sim.gesture("r", dx=-45))
step("crop_top_in", sim.gesture("t", dy=+30))
step("crop_bottom_in", sim.gesture("b", dy=-25))
step("uncrop_top_out", sim.gesture("t", dy=-15))
step("overshoot_right_out", sim.gesture("r", dx=+300))
step("corner_bl_in", sim.gesture("lb", dx=+20, dy=-20))
step("tiny_min_clamp", sim.gesture("r", dx=-2000))
step("undo_tiny", sim.gesture("r", dx=+160))
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")][0]; const s={}; 
  s.pipcropHint = !!w.document.getElementById("pipcrop-hint") && !w.document.getElementById("pipcrop-hint").hidden; return s;""")
step("reset_api", sim.player("resetCrop"))
t.close_all()
t.close()
