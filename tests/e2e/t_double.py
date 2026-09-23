"""Two copies of the module (e.g. the extension plus the Firefox AutoConfig
files): the second install() must leave the first in charge, and PiP windows
opened afterwards get exactly one crop controller."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, time
import piptest as pip

t = pip.T()
t.close_all()
first = t.install()
print("first copy:", first)
r = t.chrome("""
  const bw = Services.wm.getMostRecentWindow("navigator:browser");
  const scope = { Services, ChromeUtils, Cc, Ci, Cu };
  Services.scriptloader.loadSubScriptWithOptions(arguments[0] + "?second=" + Date.now(), { target: scope, allowUnsafeURL: true });
  const second = scope.PipCrop;
  second.install();
  bw.__secondCopy = second;
  const P = ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture;
  return { secondInstalled: second.installed, handleIsFirst: P.__pipcrop === PC, firstInstalled: PC.installed };
""", pip.MODULE)
print("after second install():", r)
assert r == {"secondInstalled": False, "handleIsFirst": True, "firstInstalled": True}, r

t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=1.0)
owners = t.chrome("""
  const bw = Services.wm.getMostRecentWindow("navigator:browser");
  const w = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
  return { first: !!PC.player(w), second: !!bw.__secondCopy.player(w) };""", pid)
print("controllers of the new PiP window:", owners)
assert owners == {"first": True, "second": False}, owners

st = t.player_call(pid, "setCrop", {"l": 0.1, "r": 0.1})
print("crop through the first copy:", json.dumps(st["crop"]))
assert abs(st["crop"]["l"] - 0.1) < 0.01 and abs(st["crop"]["r"] - 0.1) < 0.01, st

# uninstalling the inactive copy must not remove the active one
r = t.chrome("""
  const bw = Services.wm.getMostRecentWindow("navigator:browser");
  bw.__secondCopy.uninstall(); delete bw.__secondCopy;
  const P = ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture;
  return { handleIsFirst: P.__pipcrop === PC, firstInstalled: PC.installed };""")
print("after uninstalling the second copy:", r)
assert r == {"handleIsFirst": True, "firstInstalled": True}, r
t.close_all()
t.close()
print("DOUBLE INSTALL OK")
