"""Canvas route with cross-origin video: without CORS headers the canvas is
tainted, captureStream fails and the PiP is black."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, subprocess
import mn
m = mn.Marionette(int(os.environ.get("PIPCROP_PORT", "2829"))); m.start_session()
def cjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="content")
def xjs(code): return m.js("return (async () => {\n" + code + "\n})();", ctx="chrome")
for label, url in [("xorigin-noCORS", "http://127.0.0.1:8766/v169.mp4"), ("xorigin-CORS", "http://127.0.0.1:8767/v169.mp4&crossorigin=anonymous")]:
    xjs(open(os.path.join(HARNESS, "js", "pip_close_all.js"), encoding="utf-8").read())
    m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=" + url); time.sleep(3)
    r = cjs("""const P=window.__cropPiP; await new Promise(r=>setTimeout(r,500));
      let tainted = null; try { P.canvas.getContext('2d').getImageData(0,0,1,1); tainted = false; } catch(e) { tainted = String(e.name); }
      let cs = null; try { const s = P.canvas.captureStream(5); cs = 'ok tracks=' + s.getVideoTracks().length; } catch(e) { cs = 'THROWS ' + e.name + ': ' + e.message; }
      return {frames: P.frames, videoWH: [P.video.videoWidth, P.video.videoHeight], getImageData: tainted, captureStreamAfterTaint: cs, log: document.getElementById('log').textContent};""")
    cjs("window.__cropPiP.video.focus(); return 1;")
    xjs(open(os.path.join(HARNESS, "js", "pip_open.js"), encoding="utf-8").read()); time.sleep(3.5)
    shot = subprocess.run([sys.executable, "-W", "ignore", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot.py"), "13_" + label, "--calib", "canvas"], capture_output=True, text=True).stdout
    print(label, json.dumps(r), "\n   pip:", shot, flush=True)
m.send("WebDriver:DeleteSession")
