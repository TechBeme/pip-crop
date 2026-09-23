"""Programmatic crops (setCrop/resetCrop) on a 16:9 video: window size,
visible source region, scale and stretch after each step."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time, piptest as pip
t = pip.T()
t.close_all()
print("install:", t.install())
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=3.5)
print("pips:", json.dumps(t.pips()))
print("base  ", json.dumps(pip.shot("30_api_base")))
steps = [("X10", {"l": .1, "r": .1}), ("X10+Y10", {"t": .1, "b": .1}), ("L25", {"l": .25}), ("uncrop L->5", {"l": .05}),
         ("T30", {"t": .30}), ("B0", {"b": 0}), ("reset", None)]
for name, crop in steps:
    st = t.player_call(pid, "setCrop", crop) if crop else t.player_call(pid, "resetCrop")
    time.sleep(0.6)
    s = pip.shot("31_api_" + name.replace("+", "_").replace(" ", "_").replace(">", ""))[0]
    c = st["crop"]
    print(f"{name:12s} crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} rect={st['rect']}  ->  win={s['win']} src={s['src']} sx={s['sx']} sy={s['sy']} stretch={s['stretch']} black={s["black_px"]} edges={s["edges"]}")
t.close()
