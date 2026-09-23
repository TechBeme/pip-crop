"""DRM (EME ClearKey) video: the canvas route only gets black pixels, while the
PiP crop still applies. Screen captures of protected video are black, so only
the geometry can be checked."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import time, json
import piptest as pip
from sim import Sim, INSTALL_FAKE
t = pip.T()
t.close_all()
print("pipcrop:", t.status(), "| eme pref:", t.chrome("return Services.prefs.getBoolPref('media.eme.enabled', false);"))
t.m.navigate("http://127.0.0.1:8765/eme.html"); time.sleep(4)
st = t.content("const v=document.querySelector('video'); return {eme: window.emeState, mediaKeys: !!v.mediaKeys, wh: [v.videoWidth, v.videoHeight], t: v.currentTime, log: document.getElementById('log').textContent};")
print("page:", st)
# canvas route on the same EME video: drawImage must not expose pixels
cv = t.content("""const v=document.querySelector('video'); const c=document.createElement('canvas'); c.width=64; c.height=36;
  const g=c.getContext('2d'); let draw='ok', px=null;
  try { g.drawImage(v,0,0,64,36); } catch(e) { draw='THROWS ' + e.name; }
  try { const d=g.getImageData(0,0,64,36).data; let s=0; for (let i=0;i<d.length;i+=4) s+=d[i]+d[i+1]+d[i+2]; px = s; } catch(e) { px='getImageData THROWS ' + e.name; }
  let cs; try { const st=c.captureStream(5); cs='ok'; } catch(e) { cs='THROWS ' + e.name; }
  return {drawImage: draw, sumOfPixelValues: px, captureStream: cs};""")
print("canvas on EME video:", cv)
assert st["eme"]["playing"], "EME playback failed"
pid = t.open_pip(wait=1.0)
t.chrome(INSTALL_FAKE)
sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 520, "w": 480, "h": 270}); time.sleep(3)
t.wait_controls_hidden()
def check(label, s):
    r = s["rect"]
    v = pip.shot(f"80_eme_{label}", rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=s["crop"])[0]["verify"]
    c = s["crop"]
    print(f"EME {label:10s} {r['w']}x{r['h']} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} | gridX {v['x']['matched']}/{v['x']['expected_lines']} rms {v['x']['rms_px']} "
          f"gridY {v['y']['matched']}/{v['y']['expected_lines']} rms {v['y']['rms_px']} scale {v['x'].get('scale')}/{v['y'].get('scale')} black {sum(v['black_px'].values())}", flush=True)
check("base", sim.state())
s1 = sim.gesture("l", dx=+48); s1 = sim.gesture("r", dx=-48); time.sleep(0.5); t.wait_controls_hidden()
check("X10", sim.state())
t.close_all(); t.close()
