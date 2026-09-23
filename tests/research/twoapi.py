"""requestPictureInPicture() from two tabs: only one API PiP window exists at
a time; a vertical crop on a canvas PiP zooms instead of shrinking the window."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, subprocess
import mn
m = mn.Marionette(int(os.environ.get("PIPCROP_PORT", "2829"))); m.start_session()
def cjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="content")
def xjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="chrome")
xjs(open(os.path.join(HARNESS, "js", "pip_close_all.js"), encoding="utf-8").read())
pip_state = open(os.path.join(HARNESS, "js", "pip_state.js"), encoding="utf-8").read()
def api_pip():
    cjs("window.__cropPiP.makeVirtual('dom'); await new Promise(r=>setTimeout(r,800)); return 1;")
    el = m.send("WebDriver:FindElement", {"using": "css selector", "value": "#pipbtn"})
    m.send("WebDriver:ElementClick", {"id": list(el["value"].values())[0]})
    time.sleep(2.5)
m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v169.mp4"); time.sleep(2.5)
api_pip()
print("after tab A api pip:", xjs(pip_state))
nt = m.send("WebDriver:NewWindow", {"type": "tab", "focus": True})
m.send("WebDriver:SwitchToWindow", {"handle": nt["handle"], "focus": True})
m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v43.mp4"); time.sleep(2.5)
api_pip()
print("after tab B api pip:", xjs(pip_state))
# vertical crop on tab B's canvas PiP: T(10) + B(10)
s = cjs("const P=window.__cropPiP; P.T(10); P.B(10); await new Promise(r=>setTimeout(r,1500)); return P.status();")
print("tab B after T10+B10:", s["canvas"], s["virtual"], xjs(pip_state))
time.sleep(1)
print(subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.py"), "12_canvas_vcrop", "--calib", "canvas", "--wh", "1440", "1080"], capture_output=True, text=True).stdout)
m.send("WebDriver:DeleteSession")
