"""EME video is protected from screen capture: PrintWindow of the tab and of
the PiP window gives black pixels."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import time, ctypes, numpy as np
import piptest as pip, winutil as W
from sim import Sim, INSTALL_FAKE
u = ctypes.windll.user32
t = pip.T()
t.close_all()
pid = t.chrome("return Services.appinfo.processID;")
main = [x for x in W.windows(pid=pid, visible=False) if x["cls"] == "MozillaWindowClass" and x["title"]][0]["hwnd"]
u.ShowWindow(main, 4)                                   # SW_SHOWNOACTIVATE (restore, no focus)
u.SetWindowPos(main, 1, 60, 300, 900, 700, 0x10)       # HWND_BOTTOM, NOACTIVATE
time.sleep(1.0)
def tab_video_pixels(label):
    r = t.chrome("""const bw=Services.wm.getMostRecentWindow("navigator:browser"); const b=bw.gBrowser.selectedBrowser.getBoundingClientRect();
      return [bw.mozInnerScreenX - bw.screenX, bw.mozInnerScreenY - bw.screenY, b.left, b.top, bw.devicePixelRatio];""")
    vr = t.content("const e=document.querySelector('video').getBoundingClientRect(); return [e.left, e.top, e.width, e.height];")
    im, ok = W.print_window(main)
    d = r[4]
    x0, y0 = (r[0] + r[2] + vr[0]) * d, (r[1] + r[3] + vr[1]) * d
    crop = im.crop((int(x0) + 4, int(y0) + 4, int(x0 + vr[2] * d) - 4, int(y0 + vr[3] * d) - 44))
    a = np.asarray(crop)
    print(f"{label:22s} PrintWindow ok={ok} video region mean RGB {a.reshape(-1,3).mean(axis=0).round(1)} black fraction {round(float((a.max(axis=2) < 14).mean()), 3)}", flush=True)
    return crop
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(2.5)
tab_video_pixels("tab, normal video").save(os.path.join(pip.SHOTS, "82_tab_normal.png"))
t.m.navigate("http://127.0.0.1:8765/eme.html"); time.sleep(4)
print("eme state:", t.content("return window.emeState;"))
tab_video_pixels("tab, EME ClearKey").save(os.path.join(pip.SHOTS, "82_tab_eme.png"))
# PiP of the EME video, captured with PrintWindow as well
pp = t.open_pip(wait=1.0)
t.chrome(INSTALL_FAKE); sim = Sim(t, pp)
sim.player("setRect", {"x": 60, "y": 520, "w": 480, "h": 270}); time.sleep(3)
h = sim.hwnd()
im, ok = W.print_window(h); a = np.asarray(im)
print(f"PiP EME (PrintWindow)  ok={ok} mean RGB {a.reshape(-1,3).mean(axis=0).round(1)} black fraction {round(float((a.max(axis=2) < 14).mean()), 3)}")
im.save(os.path.join(pip.SHOTS, "82_pip_eme_printwindow.png"))
sim.gesture("l", dx=+48); sim.gesture("r", dx=-48)
s = sim.state(); print("PiP EME after Shift crop gestures:", s["rect"], {k: round(v, 3) for k, v in s["crop"].items()})
h = sim.hwnd(); im, ok = W.print_window(h); a = np.asarray(im)
print(f"PiP EME cropped (PrintWindow) mean RGB {a.reshape(-1,3).mean(axis=0).round(1)} black fraction {round(float((a.max(axis=2) < 14).mean()), 3)}")
im.save(os.path.join(pip.SHOTS, "82_pip_eme_cropped_printwindow.png"))
t.close_all()
u.ShowWindow(main, 6)
t.close()
