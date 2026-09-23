"""Captures while ARMED (modifier on an edge, before pressing) and while HOLDING
mid-gesture, with the black-band metric that sees through the hint outline."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import ctypes, json, time
import piptest as pip, winutil as W
from sim import Sim, INSTALL_FAKE, SWP
t = pip.T()
t.close_all(); t.install(); t.chrome(INSTALL_FAKE)
res = []
for vid, W_, H_, rect in (("v43.mp4", 1440, 1080, {"x": 60, "y": 460, "w": 440, "h": 330}),
                          ("v169.mp4", 1920, 1080, {"x": 60, "y": 460, "w": 480, "h": 270})):
    t.close_all()
    t.m.navigate(f"http://127.0.0.1:8765/video.html?src={vid}"); time.sleep(1.5)
    pid = t.open_pip(wait=0.8); sim = Sim(t, pid)
    sim.player("setRect", rect); time.sleep(2.0)
    for crop in ({"l": 0, "r": 0, "t": 0, "b": 0}, {"l": 0.1, "r": 0.02, "t": 0.08, "b": 0.01}):
        sim.player("setCrop", crop); time.sleep(0.6)
        for e in ("r", "l", "t", "b", "rb", "lt"):
            s0 = sim.state(); r = s0["rect"]
            sim.set(mod=True, button=False, inMove=False, cursor=Sim.edge_point(r, e)); time.sleep(0.35)
            sa = sim.state()
            va = pip.shot("98_armed", W_, H_, rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=sa["crop"])[0].get("verify", {})
            # press and pull outward a bit, then capture while still "holding"
            h = sim.hwnd()
            sim.set(button=True, inMove=True)
            mw, mh = sim.constraints()
            x, y, w, hh = r["x"], r["y"], r["w"], r["h"]
            if "r" in e: w = min(w + 60, mw or 10**6)
            if "l" in e:
                nw = min(w + 60, mw or 10**6); x -= nw - w; w = nw
            if "b" in e: hh = min(hh + 60, mh or 10**6)
            if "t" in e:
                nh = min(hh + 60, mh or 10**6); y -= nh - hh; hh = nh
            ctypes.windll.user32.SetWindowPos(h, 0, x, y, w, hh, SWP); time.sleep(0.35)
            sg = sim.state(); rg = sg["rect"]
            vg = pip.shot("98_holding", W_, H_, rect=(rg["x"], rg["y"], rg["x"] + rg["w"], rg["y"] + rg["h"]), crop=sg["crop"])[0].get("verify", {})
            sim.set(button=False, inMove=False); time.sleep(0.35); sim.set(mod=False); time.sleep(0.35)
            sim.player("setCrop", crop); time.sleep(0.4)
            ok = sum(va.get("black_bands", {"x": 9}).values()) == 0 and sum(vg.get("black_bands", {"x": 9}).values()) == 0
            line = f"{'PASS' if ok else 'FAIL'} {vid:9s} crop={'yes' if crop['l'] else 'no '} edge={e:2s} armed={sa['armed'] is not None} bands_armed={va.get('black_bands')} bands_holding={vg.get('black_bands')} holdRect={rg['w']}x{rg['h']}"
            print(line, flush=True); res.append(ok)
print("ALL PASS" if all(res) else f"FAILURES: {res.count(False)}")
t.close_all(); t.close()
