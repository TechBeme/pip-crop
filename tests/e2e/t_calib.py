"""Arming: with the modifier held on an edge, the size limit Windows gets must
match the distance to the video edge, uncropped and cropped."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip
from sim import Sim, INSTALL_FAKE
t = pip.T(); t.close_all(); t.install(); t.chrome(INSTALL_FAKE)
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8); sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 520, "w": 480, "h": 270}); time.sleep(1.5)
print("slack:", sim.state()["slack"], "| unconstrained maxTrack:", sim.constraints())
def arm_and_measure(label, edges):
    st = sim.state(); r = st["rect"]
    sim.set(mod=True, button=False, cursor=Sim.edge_point(r, edges)); time.sleep(0.25)
    st2 = sim.state(); mt = sim.constraints()
    c = st["crop"]; fw = r["w"] / (1 - c["l"] - c["r"]); fh = fw * 9 / 16
    fx = r["x"] - c["l"] * fw; fy = r["y"] - c["t"] * fh
    want_w = round(r["x"] + r["w"] - fx) if "l" in edges else round(fx + fw - r["x"]) if "r" in edges else None
    want_h = round(r["y"] + r["h"] - fy) if "t" in edges else round(fy + fh - r["y"]) if "b" in edges else None
    print(f"{label:18s} armed={st2['armed']} unlocked={st2['unlocked']} | windows-limit {mt} vs video-edge ({want_w}, {want_h})", flush=True)
    sim.set(mod=False); time.sleep(0.25)
for e in ("r", "l", "b", "t", "rb"):
    arm_and_measure("uncropped " + e, e)
sim.player("setCrop", {"l": 0.1, "r": 0.15, "t": 0.1, "b": 0.05}); time.sleep(0.8)
for e in ("r", "l", "b", "t", "lt"):
    arm_and_measure("cropped " + e, e)
print("after disarm:", sim.state()["constraints"], sim.constraints(), "unlocked", sim.state()["unlocked"])
t.close_all(); t.close()
