"""Modifier pressed after the drag started (too late to arm the edge): the
right edge is still capped at the video edge."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip, winutil as W
from sim import Sim, INSTALL_FAKE
t = pip.T()
t.close_all(); t.install(); t.chrome(INSTALL_FAKE)
t.chrome('Services.prefs.setBoolPref("extensions.pipcrop.debug", true); return 1;')
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8); sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 520, "w": 480, "h": 270}); time.sleep(2.0)
sim.gesture("l", dx=+65); sim.gesture("r", dx=-81)
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]); PC.player(w).debugLog.length = 0; return 1;""", pid)
st = sim.gesture("r", dx=+300, pre=False)
for i in range(6):
    s = sim.state()
    real = [x["rect"] for x in W.windows() if x["cls"] == "MozillaDialogClass" and x["title"] == "Picture-in-Picture"]
    print(f"t+{i*0.3:.1f}s module rect {s['rect']} crop r={s['crop']['r']:.3f} constraints={s['constraints']} | OS windows {real}")
    time.sleep(0.3)
log = t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]); return PC.player(w).debugLog.filter(e => e[1] !== 'geom-decide');""", pid)
for e in log[-14:]:
    print(json.dumps(e)[:260])
t.close_all(); t.close()
