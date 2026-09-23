"""Fullscreen with crop, real video resolution/aspect switch while cropped,
fast/jittery drags, modifier hint."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, random, time
import piptest as pip, winutil as W, analyze
from sim import Sim, INSTALL_FAKE

t = pip.T()
t.close_all()
t.install() if not os.environ.get("PIPCROP_NO_INJECT") else print("using installed extension:", t.status())
t.chrome(INSTALL_FAKE)
t.chrome('Services.prefs.setBoolPref("extensions.pipcrop.debug", true); return 1;')
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8)
sim = Sim(t, pid)
sim.player("setRect", {"x": 60, "y": 400, "w": 480, "h": 270})
time.sleep(2.5)


def check(label, W_=1920, H_=1080):
    t.wait_controls_hidden()
    s = sim.state()
    r = s["rect"]
    sh = pip.shot(f"70_{label}", W_, H_, rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=s["crop"])[0]
    v = sh["verify"]
    c = s["crop"]
    print(f"{label:24s} {r['w']}x{r['h']}@{r['x']},{r['y']} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} aspect={s['aspect']:.4f} "
          f"| gridX {v['x']['matched']}/{v['x']['expected_lines']} rms {v['x']['rms_px']} gridY {v['y']['matched']}/{v['y']['expected_lines']} rms {v['y']['rms_px']} "
          f"scale {v['x'].get('scale')}/{v['y'].get('scale')} black {sum(v['black_px'].values())} gesture={s['gesture']} unlocked={s['unlocked']}", flush=True)
    return s


sim.gesture("l", dx=+60)
sim.gesture("b", dy=-40)
before = check("cropped")

# ---- 1. fullscreen: cropped region letterboxed ("contain"), no stretch ------
W.wait_idle(2000, timeout=120)
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  w.document.getElementById("fullscreen").click(); await new Promise(r => setTimeout(r, 1800));
  return [w.windowState, w.innerWidth, w.innerHeight];""", pid)
fs = sim.state()
r = fs["rect"]
c = fs["crop"]
img = W.grab((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
# expected content rect inside the fullscreen window (device px)
regA = (1920 * (1 - c["l"] - c["r"])) / (1080 * (1 - c["t"] - c["b"]))
if r["w"] / r["h"] > regA:
    ch = r["h"]; cw = ch * regA
else:
    cw = r["w"]; ch = cw / regA
ox, oy = (r["w"] - cw) / 2, (r["h"] - ch) / 2
inner = img.crop((round(ox), round(oy), round(ox + cw), round(oy + ch)))
v = analyze.verify(inner, c, 1920, 1080)
small = img.resize((img.width // 4, img.height // 4))
small.save(os.path.join(pip.SHOTS, "70_fullscreen_small.png"))
print(f"fullscreen               window {r['w']}x{r['h']} content {cw:.0f}x{ch:.0f} at +{ox:.0f},+{oy:.0f} | gridX {v['x']['matched']}/{v['x']['expected_lines']} "
      f"rms {v['x']['rms_px']} gridY {v['y']['matched']}/{v['y']['expected_lines']} rms {v['y']['rms_px']} scale {v['x'].get('scale')}/{v['y'].get('scale')} stretch {v.get('stretch')}", flush=True)
t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  w.document.getElementById("fullscreen").click(); await new Promise(r => setTimeout(r, 1500)); return w.windowState;""", pid)
after_fs = check("after_fullscreen")
assert after_fs["rect"] == before["rect"] and after_fs["crop"] == before["crop"], "fullscreen round-trip changed geometry"

# ---- 2. real resolution switch (same aspect) and aspect switch, while cropped ----
def switch(src):
    t.content("""const v=document.querySelector('video'); const tm=v.currentTime; v.src=arguments[0];
      await new Promise(r => v.addEventListener('loadeddata', r, {once:true})); v.currentTime = tm; await v.play();
      await new Promise(r => setTimeout(r, 1500)); return [v.videoWidth, v.videoHeight];""", src)
print("switch to 1280x720 (same 16:9):", switch("v169_720.mp4"))
check("res_720p", 1280, 720)
print("switch to 1440x1080 (4:3):", switch("v43.mp4"))
s43 = check("aspect_4x3", 1440, 1080)
print("switch back to 1920x1080:", switch("v169.mp4"))
check("back_1080p")

# ---- 3. fast / jittery drags ----
random.seed(7)
sim.gesture("r", dx=-90, steps=150, step_s=0.0)
check("fast_150_steps")
h = sim.hwnd()
st = sim.state(); r0 = dict(st["rect"])
sim.player("setModifier", True)
sim.set(mod=True, button=True, cursor=Sim.edge_point(r0, "l"))
x = r0["x"]; w_ = r0["w"]
for i in range(200):
    d = random.randint(-25, 25)
    x2, w2 = x + d, w_ - d
    if 170 < w2 < 700:
        x, w_ = x2, w2
        import ctypes
        ctypes.windll.user32.SetWindowPos(h, 0, x, r0["y"], w_, r0["h"], 0x14)
        sim.set(cursor={"x": x + 6, "y": r0["y"] + r0["h"] // 2})
sim.set(button=False); time.sleep(0.4); sim.set(mod=False); sim.player("setModifier", False); time.sleep(0.4)
check("jitter_200_moves")

# ---- 4. modifier hint -----------------------------------------------------
sim.player("setModifier", True)
time.sleep(0.3)
hint = t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  const e=w.document.getElementById("pipcrop-hint"); return e ? !e.hidden : null;""", pid)
s = sim.state(); r = s["rect"]
W.grab((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])).save(os.path.join(pip.SHOTS, "70_hint_visible.png"))
sim.player("setModifier", False)
time.sleep(0.3)
hint2 = t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  const e=w.document.getElementById("pipcrop-hint"); return e ? !e.hidden : null;""", pid)
print("hint visible while modifier held:", hint, "| after release:", hint2)
errs = t.chrome("""return Services.console.getMessageArray().filter(m => m instanceof Ci.nsIScriptError && /pipcrop/i.test(m.sourceName || "")).map(m => m.errorMessage + " @" + m.lineNumber);""")
print("console errors from pipcrop.js:", errs)
t.close_all()
t.close()
