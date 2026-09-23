"""The outline hint shows while the modifier is held over the window and hides
when it is released."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import time, piptest as pip, winutil as W
from sim import Sim, INSTALL_FAKE
t = pip.T(); t.close_all(); t.install(); t.chrome(INSTALL_FAKE)
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8); sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 400, "w": 480, "h": 270}); time.sleep(3)
q = """const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  const e=w.document.getElementById("pipcrop-hint"); return e ? !e.hidden : null;"""
sim.set(mod=True); sim.player("setModifier", True); time.sleep(0.5)
v1 = t.chrome(q, pid); r = sim.state()["rect"]
W.grab((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])).save(os.path.join(pip.SHOTS, "71_hint_on.png"))
sim.set(mod=False); time.sleep(0.5)          # physical Shift released -> poll hides it
v2 = t.chrome(q, pid); unlocked = sim.state()["unlocked"]
print("hint while Shift held:", v1, "| after Shift released (poll):", v2, "| aspect unlocked after release:", unlocked)
t.close_all(); t.close()
