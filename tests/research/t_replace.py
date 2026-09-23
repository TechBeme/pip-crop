"""Canvas route: after a crop, swap the MediaStream track (the video freezes)
or the srcObject (the PiP closes)."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import time, json, ctypes
import piptest as pip, winutil as W
t = pip.T()
pid = t.chrome("return Services.appinfo.processID;")
for x in W.windows(pid=pid):
    if x["cls"] == "MozillaWindowClass": ctypes.windll.user32.ShowWindow(x["hwnd"], 6)
t.chrome("""const pr = Services.scriptSecurityManager.createContentPrincipalFromOrigin("http://127.0.0.1:8765");
  Services.perms.addFromPrincipal(pr, "canvas", Services.perms.ALLOW_ACTION); return 1;""")
PIPS = """return [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].map(w => [w.screenX, w.screenY, w.outerWidth, w.outerHeight]);"""
for mode in ("replaceTrack", "replaceStream"):
    t.close_all()
    t.m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v169.mp4"); time.sleep(3)
    t.content("window.__cropPiP.video.focus(); await new Promise(r=>setTimeout(r,300)); return 1;")
    t.open_pip(wait=2.0)
    before = t.content("const P=window.__cropPiP; P.resizeEvents.length=0; return P.status();")
    pb = t.chrome(PIPS)
    # crop first (canvas 1536x1080), then swap the track/stream
    r = t.content(f"""const P=window.__cropPiP; P.X(10); await new Promise(r=>setTimeout(r,800));
      const mid = P.status(); const out = P.{mode}(); await new Promise(r=>setTimeout(r,1500));
      const after = P.status();
      return {{mid: {{video: mid.virtual, settings: mid.trackSettings, resizeEvents: mid.resizeEvents.length}},
               after: {{video: after.virtual, settings: after.trackSettings, resizeEvents: after.resizeEvents.map(e => e[0] + 'x' + e[1]), readyState: after.readyState, paused: after.paused}}}};""")
    pa = t.chrome(PIPS)
    # a further crop change after the swap
    r2 = t.content("""const P=window.__cropPiP; P.X(20); await new Promise(r=>setTimeout(r,1200)); const s=P.status();
      return {video: s.virtual, settings: s.trackSettings, resizeEvents: s.resizeEvents.map(e => e[0] + 'x' + e[1])};""")
    pc = t.chrome(PIPS)
    print(f"== {mode}")
    print("   before crop : video", before["virtual"], "settings", before["trackSettings"], "| PiP", pb)
    print("   after X(10)  :", r["mid"])
    print(f"   after {mode}:", r["after"], "| PiP", pa)
    print("   then X(20)   :", r2, "| PiP", pc, flush=True)
t.close_all()
t.m.send("Marionette:Quit", {"flags": ["eForceQuit"]})
