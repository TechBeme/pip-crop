"""shot.py <name> [--calib NAME] [--make-calib NAME] [--wh W H]
Screenshot all PiP windows of the test browser and analyze them."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, argparse
import winutil as w, analyze as A, paths
ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("--calib", default="native")
ap.add_argument("--make-calib", default=None); ap.add_argument("--wh", nargs=2, type=int, default=[1920, 1080])
ap.add_argument("--full", action="store_true")
a = ap.parse_args()
W, H = a.wh
out_dir = str(paths.OUT)
pips = [x for x in w.windows() if x["cls"] == "MozillaDialogClass" and x["title"] == "Picture-in-Picture"]
out = []
for i, p in enumerate(sorted(pips, key=lambda x: x["rect"])):
    im = w.grab(p["rect"])
    im.save(os.path.join(paths.SHOTS, f"{a.name}_{i}.png"))
    if a.make_calib:
        c = A.calibrate(im, W, H)
        json.dump([float(x) for x in c], open(os.path.join(out_dir, f"calib_{a.make_calib}.json"), "w"))
    cf = os.path.join(out_dir, f"calib_{a.make_calib or a.calib}.json")
    calib = tuple(json.load(open(cf))) if os.path.exists(cf) else None
    r = A.analyze(im, W, H, calib)
    r.pop("fit", None)
    r["rect"] = p["rect"]
    r["win"] = [p["rect"][2] - p["rect"][0], p["rect"][3] - p["rect"][1]]
    if not a.full:
        g = r.get("grid", {})
        r = {"win": r["win"], "rect": r["rect"], "black_px": r["black_px"], "any_black": round(r["black"]["any_black_px"], 4),
             "grid": g, "color": {k: r.get(k) for k in ("x0", "x1", "y0", "y1", "stretch")}}
    out.append(r)
print(json.dumps(out))
