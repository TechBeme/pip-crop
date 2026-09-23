"""Installs the built .xpi (python tools/build.py) into the test browser without
a restart, then restarts the browser: the extension must come back by itself."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import glob, time, json
import piptest as pip, mn, paths
XPI = max(glob.glob(str(paths.DIST / "pip-crop-*.xpi")), key=os.path.getmtime)
ADDON_ID = json.load(open(paths.DIST / "extension" / "manifest.json"))["browser_specific_settings"]["gecko"]["id"]
t = pip.T()
t.close_all()
print("before:", t.status())
t.chrome("if (PC && PC.installed) PC.uninstall(); return 1;")
print("after removing injected copy:", t.status())
t.chrome("""Services.prefs.setBoolPref("xpinstall.signatures.required", false);
  Services.prefs.setBoolPref("extensions.experiments.enabled", true); return 1;""")
r = t.m.send("Addon:Install", {"path": XPI, "temporary": False})
print("Addon:Install ->", r)
time.sleep(1.0)
print("after install (no restart):", t.status())
addon = t.chrome("""const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
  const a = await AddonManager.getAddonByID(arguments[0]);
  return a && { name: a.name, version: a.version, isActive: a.isActive, signedState: a.signedState, temporarilyInstalled: a.temporarilyInstalled, isPrivileged: a.isPrivileged };""", ADDON_ID)
print("addon:", addon)
# full browser restart: extension must come back by itself at startup
try:
    t.m.send("Marionette:Quit", {"flags": ["eRestart"]})
except Exception as e:
    print("quit:", e)
t.m.sock.close()
time.sleep(4)
t2 = pip.T()
print("after RESTART:", t2.status())
print("prefs:", t2.chrome("""return ["xpinstall.signatures.required","extensions.experiments.enabled"].map(p => p + "=" + Services.prefs.getBoolPref(p));"""))
t2.close()
