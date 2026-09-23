"""Real input (SendInput): a plain corner drag on a cropped window resizes
proportionally and keeps the crop."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, piptest as pip, winutil as W
t = pip.T()
t.chrome('PC._setNativeForTests(null); Services.prefs.setBoolPref("extensions.pipcrop.debug", true); return 1;')
t.close_all()
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8)
t.player_call(pid, "setRect", {"x": 60, "y": 470, "w": 600, "h": 338})
t.player_call(pid, "setCrop", {"l": 0.05, "r": 0.1, "t": 0.1, "b": 0.1})
time.sleep(2.5)
def st(): return [x for x in t.pips() if x["id"] == pid][0]["crop"]
def dump():
    return t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
      const p=PC.player(w); const l=p.debugLog.slice(); p.debugLog.length=0; return l;""", pid)
dump()
r = st()["rect"]; print("before", r, st()["crop"])
import ctypes
from ctypes import wintypes
u = ctypes.windll.user32; u.SendMessageW.restype = ctypes.c_ssize_t
u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
h = t.hwnd_of((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
for (dx, dy) in [(7, 7), (3, 3), (12, 12)]:
    x, y = r["x"] + r["w"] - 1 - dx, r["y"] + r["h"] - 1 - dy
    print("hit-test at corner inset", dx, "=", u.SendMessageW(h, 0x84, 0, ((y & 0xFFFF) << 16) | (x & 0xFFFF)), "(17=BOTTOMRIGHT)")
W.wait_idle(5000, timeout=3600)
x0, y0 = r["x"] + r["w"] - 8, r["y"] + r["h"] - 8
W.drag(x0, y0, x0 + 48, y0 + 27, steps=22, step_ms=14, shift=False)
time.sleep(1.0)
print("after corner drag", st()["rect"], {k: round(v, 3) for k, v in st()["crop"].items()})
for e in dump()[:40]:
    print(json.dumps(e))
t.close()
