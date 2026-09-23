"""Canvas route (www/canvas_crop.html): does a captureStream PiP keep updating
while its tab is in the background?"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, subprocess
import mn
m = mn.Marionette(int(os.environ.get("PIPCROP_PORT", "2829"))); m.start_session()
def cjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="content")
def xjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="chrome")
xjs(open(os.path.join(HARNESS, "js", "pip_close_all.js"), encoding="utf-8").read())
m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v169.mp4"); time.sleep(2.5)
cjs("window.__cropPiP.makeVirtual('dom'); await new Promise(r=>setTimeout(r,800)); return 1;")
el = m.send("WebDriver:FindElement", {"using": "css selector", "value": "#pipbtn"})
m.send("WebDriver:ElementClick", {"id": list(el["value"].values())[0]})
time.sleep(2.5)
tabA = m.send("WebDriver:GetWindowHandle")["value"]
def frames(): return cjs("const P=window.__cropPiP; return {frames: P.frames, t: P.source.currentTime.toFixed(2), hidden: document.hidden};")
f0 = frames(); time.sleep(2); f1 = frames()
print("foreground:", f0, f1, flush=True)
subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.py"), "10_bg_fore", "--calib", "canvas"], capture_output=True)
# open tab B and select it -> tab A goes to background
nt = m.send("WebDriver:NewWindow", {"type": "tab", "focus": True})
m.send("WebDriver:SwitchToWindow", {"handle": nt["handle"], "focus": True})
m.navigate("http://127.0.0.1:8765/video.html?src=v43.mp4"); time.sleep(1)
m.send("WebDriver:SwitchToWindow", {"handle": tabA, "focus": False})
time.sleep(0.5)
g0 = frames(); time.sleep(3); g1 = frames()
print("background:", g0, g1, flush=True)
a = subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.py"), "11_bg_back_a", "--calib", "canvas"], capture_output=True, text=True).stdout
time.sleep(2)
b = subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.py"), "11_bg_back_b", "--calib", "canvas"], capture_output=True, text=True).stdout
sel = xjs("const bw=Services.wm.getMostRecentWindow('navigator:browser'); return bw.gBrowser.selectedBrowser.currentURI.spec;")
print("selected tab:", sel)
m.send("WebDriver:DeleteSession")
