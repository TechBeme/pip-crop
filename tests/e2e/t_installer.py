"""The Windows installer end to end, against test targets: two LibreWolf profiles
(one with a user.js and a pref of its own, one without) and a portable copy of
Firefox. Installs silently, checks that PiP Crop runs and crops in both browsers,
uninstalls, and checks that everything is back to how it was.

Needs the test build of the installer, which requires no elevation:
    ISCC /DAppVersion=X.Y.Z /DTestBuild installer\\pip-crop.iss
    python tests/e2e/t_installer.py dist\\pip-crop-X.Y.Z-setup.exe
"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, shutil, subprocess, time
import mn, paths, piptest as pip

SETUP = os.path.abspath(sys.argv[1])
WORK = paths.OUT / "installer"
LWDATA = WORK / "lwdata"
PROF_A = paths.PROFILES / "inst-lw-a"           # absolute path in profiles.ini, has a user.js
PROF_B = LWDATA / "Profiles" / "rel.default"    # relative path, no user.js, a pref of its own
FIREFOX = WORK / "firefox"
APP = WORK / "app"
ADDON_ID = "pip-crop@techbeme.github.io"
PORT_LW, PORT_FF = 2841, 2842
PREFS = ["xpinstall.signatures.required", "extensions.experiments.enabled",
         "extensions.startupScanScopes", "extensions.autoDisableScopes"]
failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {label}{' | ' + str(detail) if detail else ''}", flush=True)
    if not ok:
        failures.append(label)


def run_setup(*args):
    r = subprocess.run([SETUP, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", *args])
    return r.returncode


def start_browser(exe, profile, port):
    """Starts a browser on a profile without touching its user.js."""
    proc = subprocess.Popen([exe, "-no-remote", "-new-instance", "-profile", str(profile), "--marionette",
                             "--remote-allow-system-access"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    m = mn.Marionette(port)
    m.start_session()
    m.proc = proc
    return m


def addon_state(m):
    return m.js("""return (async () => { const { AddonManager } = ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');
      const a = await AddonManager.getAddonByID(arguments[0]);
      const P = ChromeUtils.importESModule('moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs').PictureInPicture;
      for (let i = 0; i < 20 && a && !P.__pipcrop; i++) await new Promise(r => setTimeout(r, 250));
      return { addon: a ? { version: a.version, active: a.isActive } : null, module: P.__pipcrop ? P.__pipcrop.version : null,
               prefs: arguments[1].map(p => [p, Services.prefs.prefHasUserValue(p)]) }; })();""", ADDON_ID, PREFS)


def crop_works(port):
    t = pip.T(port)
    t.close_all()
    t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
    pid = t.open_pip(wait=1.0)
    t.player_call(pid, "setRect", {"x": 60, "y": 520, "w": 480, "h": 270})
    st = t.player_call(pid, "setCrop", {"l": 0.1, "r": 0.1})
    t.close_all()
    t.close()
    return st["rect"]["w"], st["rect"]["h"]


def quit_browser(port, profile=None):
    m = mn.Marionette(port)
    m.start_session()
    m.quit()
    for _ in range(40):  # wait until the profile is released
        lock = profile / "parent.lock" if profile else None
        try:
            if lock is None or not lock.exists():
                break
            lock.unlink()
            break
        except OSError:
            time.sleep(0.5)
    time.sleep(1)


def read(p):
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    # profile A: made by the harness (it has a user.js)
    m = mn.launch("librewolf", "inst-lw-a", PORT_LW); time.sleep(1.5); m.quit(); time.sleep(3)
    # profile B: relative path, then drop its user.js and give it its own value for a pref the installer sets
    m = mn.launch("librewolf", os.path.relpath(PROF_B, paths.PROFILES), PORT_LW); time.sleep(1.5); m.quit(); time.sleep(3)
    (PROF_B / "user.js").unlink()
    with open(PROF_B / "prefs.js", "a", encoding="utf-8") as f:
        f.write('user_pref("extensions.startupScanScopes", 5);\n')
    (LWDATA / "profiles.ini").write_text(
        "[General]\nStartWithLastProfile=1\n\n"
        f"[Profile0]\nName=a\nIsRelative=0\nPath={PROF_A}\n\n"
        "[Profile1]\nName=b\nIsRelative=1\nPath=Profiles/rel.default\n", encoding="utf-8")
    subprocess.run(["robocopy", r"C:\Program Files\Mozilla Firefox", str(FIREFOX), "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
                   stdout=subprocess.DEVNULL)
    user_js_a = read(PROF_A / "user.js")
    prefs_b = read(PROF_B / "prefs.js")

    code = run_setup(f"/DIR={APP}", f"/LIBREWOLFDATA={LWDATA}", f"/FIREFOXDIRS={FIREFOX}", f"/LOG={WORK / 'install.log'}")
    check("setup exit code 0", code == 0, code)
    for name, prof in (("A", PROF_A), ("B", PROF_B)):
        check(f"profile {name}: extension copied", (prof / "extensions" / f"{ADDON_ID}.xpi").exists())
        uj = read(prof / "user.js") or ""
        check(f"profile {name}: prefs block in user.js", uj.count("// >>> PiP Crop") == 1 and all(p in uj for p in PREFS))
    check("profile A: its own user.js lines kept", user_js_a.strip() in (read(PROF_A / "user.js") or ""))
    check("Firefox: AutoConfig files", all((FIREFOX / f).exists() for f in ("pipcrop.cfg", "pipcrop.js", r"defaults\pref\autoconfig.js")))

    # a second run (upgrade / repair) must not duplicate anything
    code = run_setup(f"/DIR={APP}", f"/LIBREWOLFDATA={LWDATA}", f"/FIREFOXDIRS={FIREFOX}")
    check("second run: exit code 0, single prefs block", code == 0 and (read(PROF_A / "user.js") or "").count("// >>> PiP Crop") == 1)

    m = start_browser(mn.BROWSERS["librewolf"], PROF_A, PORT_LW)
    st = addon_state(m)
    check("LibreWolf: extension installed and running on first start", st["module"] and st["addon"] and st["addon"]["active"], st)
    m.sock.close()
    check("LibreWolf: crop works", crop_works(PORT_LW) == (384, 270))
    quit_browser(PORT_LW, PROF_A)

    m = mn.launch("firefox", "inst-ff", PORT_FF, exe=str(FIREFOX / "firefox.exe"))
    st = m.js("""const P = ChromeUtils.importESModule('moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs').PictureInPicture;
      return P.__pipcrop ? P.__pipcrop.version : null;""")
    check("Firefox: PiP Crop running", bool(st), st)
    m.sock.close()
    check("Firefox: crop works", crop_works(PORT_FF) == (384, 270))
    quit_browser(PORT_FF)

    unins = next(APP.glob("unins*.exe"))
    r = subprocess.run([str(unins), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={WORK / 'uninstall.log'}"])
    for _ in range(40):  # the uninstaller finishes in a detached copy of itself
        if not APP.exists() or not any(APP.glob("unins*.exe")):
            break
        time.sleep(0.5)
    check("uninstaller removed its folder", not any(APP.glob("*")) if APP.exists() else True)
    for name, prof in (("A", PROF_A), ("B", PROF_B)):
        check(f"profile {name}: extension removed", not (prof / "extensions" / f"{ADDON_ID}.xpi").exists())
        check(f"profile {name}: prefs block removed", "PiP Crop" not in (read(prof / "user.js") or ""))
    check("profile A: user.js back to what it was", (read(PROF_A / "user.js") or "").strip() == user_js_a.strip())
    check("profile B: its own startupScanScopes=5 restored", 'user_pref("extensions.startupScanScopes", 5);' in (read(PROF_B / "prefs.js") or ""))
    check("profile B: signature pref not left behind", "xpinstall.signatures.required" not in (read(PROF_B / "prefs.js") or ""))
    check("Firefox: AutoConfig files removed", not any((FIREFOX / f).exists() for f in ("pipcrop.cfg", "pipcrop.js", r"defaults\pref\autoconfig.js")))

    m = start_browser(mn.BROWSERS["librewolf"], PROF_A, PORT_LW)
    st = addon_state(m)
    check("LibreWolf after uninstall: no extension, no module", st["addon"] is None and st["module"] is None, st)
    m.quit(); time.sleep(2)
    print("ALL PASS" if not failures else f"FAILED: {failures}")


if __name__ == "__main__":
    main()
