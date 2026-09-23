"""Cross-origin video served without CORS headers (port 8766): the page cannot
read its pixels, but the PiP crop does not need to. Crops it and verifies the
visible region, scale and black bands from screenshots."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip

t = pip.T()
t.close_all()
print("module:", t.install())
t.m.navigate("http://127.0.0.1:8765/video.html?src=http://127.0.0.1:8766/v169.mp4"); time.sleep(2.0)
page = t.content("""const v = document.querySelector('video'); const c = document.createElement('canvas');
  c.width = 8; c.height = 8; const g = c.getContext('2d'); g.drawImage(v, 0, 0, 8, 8);
  let read; try { g.getImageData(0, 0, 1, 1); read = 'readable'; } catch (e) { read = e.name; }
  return { size: [v.videoWidth, v.videoHeight], playing: !v.paused, canvasRead: read };""")
print("page:", page)
assert page["canvasRead"] == "SecurityError" and page["size"] == [1920, 1080], page
pid = t.open_pip(wait=1.0)
t.player_call(pid, "setRect", {"x": 60, "y": 520, "w": 480, "h": 270})
time.sleep(2.5)
ok = True
for label, crop in (("base", {"l": 0, "r": 0, "t": 0, "b": 0}), ("lr10", {"l": 0.1, "r": 0.1}),
                    ("all4", {"l": 0.1, "r": 0.05, "t": 0.1, "b": 0.08})):
    st = t.player_call(pid, "setCrop", crop)
    time.sleep(0.6)
    t.wait_controls_hidden()
    r = st["rect"]
    sh = pip.shot(f"90_xorigin_{label}", rect=(r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]), crop=st["crop"])[0]
    if sh.get("missing") or sh.get("occluded"):
        print(label, "capture skipped (PiP not visible)")
        continue
    v = sh["verify"]
    good = v["x"]["matched"] == v["x"]["expected_lines"] and v["y"]["matched"] == v["y"]["expected_lines"] \
        and not any(v["black_bands"].values())
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} {label:5s} {r['w']}x{r['h']} crop {json.dumps({k: round(x, 3) for k, x in st['crop'].items()})} "
          f"grid {v['x']['matched']}/{v['x']['expected_lines']}+{v['y']['matched']}/{v['y']['expected_lines']} "
          f"scale {v['x'].get('scale')}/{v['y'].get('scale')} bands {v['black_bands']}")
t.close_all()
t.close()
print("ALL PASS" if ok else "FAILED")
