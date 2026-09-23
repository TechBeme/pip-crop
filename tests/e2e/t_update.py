"""Self-hosted updates: an installed build finds a newer version through its
update_url and installs it, without a restart, in the format tools/build.py
writes (build with --repo first, so dist/updates.json exists).

The update manifest is served from a local HTTP server, so the test profile
gets extensions.checkUpdateSecurity=false; released builds use https (GitHub)."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import functools, hashlib, http.server, json, threading, time, zipfile
import piptest as pip, paths

PORT = 8799
EXT = paths.DIST / "extension"
WORK = paths.OUT / "update"
WORK.mkdir(parents=True, exist_ok=True)
requests = []


def build_xpi(version):
    """dist/extension with another version and a local update_url."""
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
    old = manifest["version"]
    manifest["version"] = version
    manifest["browser_specific_settings"]["gecko"]["update_url"] = f"http://127.0.0.1:{PORT}/updates.json"
    api = (EXT / "api.js").read_text(encoding="utf-8")
    assert api.count(f'version: "{old}",') == 1
    out = WORK / f"pip-crop-{version}.xpi"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("schema.json", (EXT / "schema.json").read_text(encoding="utf-8"))
        z.writestr("api.js", api.replace(f'version: "{old}",', f'version: "{version}",'))
        z.writestr("icons/pip-crop.svg", (EXT / "icons" / "pip-crop.svg").read_text(encoding="utf-8"))
    return out, manifest


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        requests.append(self.path)


base = json.loads((paths.DIST / "updates.json").read_text(encoding="utf-8"))
v1 = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["version"]
v2 = v1 + ".1"
xpi1, manifest = build_xpi(v1)
xpi2, _ = build_xpi(v2)
addon_id = manifest["browser_specific_settings"]["gecko"]["id"]
entry = base["addons"][addon_id]["updates"][0]
entry.update(version=v2, update_link=f"http://127.0.0.1:{PORT}/{xpi2.name}",
             update_hash="sha256:" + hashlib.sha256(xpi2.read_bytes()).hexdigest())
(WORK / "updates.json").write_text(json.dumps(base, indent=2), encoding="utf-8")
server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Handler, directory=str(WORK)))
threading.Thread(target=server.serve_forever, daemon=True).start()

t = pip.T()
t.close_all()
t.chrome("""
  Services.prefs.setBoolPref("xpinstall.signatures.required", false);
  Services.prefs.setBoolPref("extensions.experiments.enabled", true);
  Services.prefs.setBoolPref("extensions.checkUpdateSecurity", false);
  const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
  const old = await AddonManager.getAddonByID(arguments[0]);
  if (old) await old.uninstall();
  if (PC && PC.installed) PC.uninstall();   // an injected copy would keep the extension inactive
  return 1;""", addon_id)
print("install", xpi1.name, "->", t.m.send("Addon:Install", {"path": str(xpi1), "temporary": False}))
time.sleep(1.0)
ADDON = """const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
  const a = await AddonManager.getAddonByID(arguments[0]);"""
before = t.chrome(ADDON + " return { version: a.version, active: a.isActive, module: PC && PC.version };", addon_id)
print("installed:", before)
assert before == {"version": v1, "active": True, "module": v1}, before

result = t.chrome(ADDON + """
  return await new Promise(resolve => {
    setTimeout(() => resolve({ timeout: true }), 30000);
    a.findUpdates({
      onUpdateAvailable(addon, install) {
        install.addListener({
          onInstallEnded: (i, n) => resolve({ installed: n.version }),
          onInstallFailed: i => resolve({ installFailed: i.error }),
          onDownloadFailed: i => resolve({ downloadFailed: i.error }),
        });
        install.install();
      },
      onNoUpdateAvailable: () => resolve({ noUpdate: true }),
      onUpdateFinished: (addon, error) => { if (error) resolve({ updateError: error }); },
    }, AddonManager.UPDATE_WHEN_USER_REQUESTED);
  });""", addon_id)
print("update check:", result, "| server saw:", requests)
time.sleep(1.5)
after = t.chrome(ADDON + " return { version: a.version, active: a.isActive, module: PC && PC.version };", addon_id)
print("after update:", after)
assert result == {"installed": v2} and after == {"version": v2, "active": True, "module": v2}, (result, after)
assert "/updates.json" in requests and f"/{xpi2.name}" in requests, requests

t.chrome(ADDON + " await a.uninstall(); return 1;", addon_id)
t.close()
server.shutdown()
print("UPDATE OK")
