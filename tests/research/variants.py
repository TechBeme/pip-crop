"""Canvas route: the captureStream <video> in different states (in the DOM,
hidden, tiny, detached). Does the PiP follow when the canvas is resized?"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, subprocess
import mn
m = mn.Marionette(int(os.environ.get("PIPCROP_PORT", "2829"))); m.start_session()
def cjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="content")
def xjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="chrome")
close_all = open(os.path.join(HARNESS, "js", "pip_close_all.js"), encoding="utf-8").read()
pip_state = open(os.path.join(HARNESS, "js", "pip_state.js"), encoding="utf-8").read()
results = {}
for mode in ["dom", "hidden", "tiny", "detached"]:
    xjs(close_all)
    m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v169.mp4")
    time.sleep(2.5)
    cjs(f"window.__cropPiP.makeVirtual('{mode}'); await new Promise(r=>setTimeout(r,800)); return 1;")
    el = m.send("WebDriver:FindElement", {"using": "css selector", "value": "#pipbtn"})
    eid = list(el["value"].values())[0] if isinstance(el.get("value"), dict) else list(el.values())[0]
    m.send("WebDriver:ElementClick", {"id": eid})
    time.sleep(2.5)
    before = xjs(pip_state)
    s0 = cjs("return window.__cropPiP.status();")
    cjs("window.__cropPiP.X(10); await new Promise(r=>setTimeout(r,1500)); return 1;")
    s1 = cjs("return window.__cropPiP.status();")
    after = xjs(pip_state)
    results[mode] = {"pip_before": before, "pip_after": after,
                     "video_before": s0["virtual"], "video_after": s1["virtual"],
                     "settings_after": s1["trackSettings"], "canvas_after": s1["canvas"],
                     "resize_events": s1["resizeEvents"], "log": cjs("return document.getElementById('log').textContent")}
    print(mode, json.dumps(results[mode]), flush=True)
m.send("WebDriver:DeleteSession")
