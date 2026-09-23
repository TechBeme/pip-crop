"""Minimal Marionette (protocol 3) client + LibreWolf/Firefox launcher for tests.

Runs the real browser with an isolated profile, -no-remote, and chrome-context
access (--remote-allow-system-access), so tests can execute privileged JS in
the parent process (including inside PiP player windows).
"""
import json, os, socket, subprocess, time, shutil
import paths

# Override with PIPCROP_LIBREWOLF / PIPCROP_FIREFOX (full path to the .exe).
BROWSERS = {
    "librewolf": os.environ.get("PIPCROP_LIBREWOLF") or r"C:\Program Files\LibreWolf\librewolf.exe",
    "firefox": os.environ.get("PIPCROP_FIREFOX") or r"C:\Program Files\Mozilla Firefox\firefox.exe",
}

BASE_PREFS = {
    "browser.shell.checkDefaultBrowser": False,
    "browser.startup.homepage_override.mstone": "ignore",
    "browser.aboutwelcome.enabled": False,
    "browser.startup.page": 0,
    "browser.tabs.warnOnClose": False,
    "browser.warnOnQuit": False,
    "browser.sessionstore.resume_from_crash": False,
    "datareporting.policy.dataSubmissionPolicyBypassNotification": True,
    "toolkit.telemetry.reportingpolicy.firstRun": False,
    "media.autoplay.default": 0,
    "media.autoplay.blocking_policy": 0,
    "media.videocontrols.picture-in-picture.enabled": True,
    "dom.security.https_only_mode": False,
    "devtools.chrome.enabled": True,
    "browser.translations.automaticallyPopup": False,
    "sidebar.revamp": False,
    "media.block-autoplay-until-in-foreground": False,
    "browser.sessionstore.max_resumed_crashes": -1,
}


class MarionetteError(Exception):
    pass


class Marionette:
    def __init__(self, port, host="127.0.0.1", timeout=60):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                self.sock = socket.create_connection((host, port), timeout=5)
                break
            except OSError as e:
                last = e
                time.sleep(0.3)
        else:
            raise MarionetteError(f"cannot connect to marionette on {port}: {last}")
        self.sock.settimeout(300)
        self.buf = b""
        self.msgid = 0
        hello = self._recv()
        self.hello = hello
        self.context = "content"

    def _recv(self):
        while b":" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise MarionetteError("connection closed")
            self.buf += chunk
        length, rest = self.buf.split(b":", 1)
        length = int(length)
        while len(rest) < length:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise MarionetteError("connection closed")
            rest += chunk
        msg, self.buf = rest[:length], rest[length:]
        return json.loads(msg)

    def send(self, command, params=None):
        self.msgid += 1
        data = json.dumps([0, self.msgid, command, params or {}]).encode()
        self.sock.sendall(str(len(data)).encode() + b":" + data)
        while True:
            resp = self._recv()
            if resp[0] == 1 and resp[1] == self.msgid:
                break
        _, _, err, result = resp
        if err:
            raise MarionetteError(f"{command}: {err.get('error')}: {err.get('message')}\n{err.get('stacktrace','')[:1500]}")
        return result

    def start_session(self):
        r = self.send("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {"moz:accessibilityChecks": False}}})
        self.send("WebDriver:SetTimeouts", {"script": 120000, "pageLoad": 60000})
        return r

    def set_context(self, ctx):
        if ctx != self.context:
            self.send("Marionette:SetContext", {"value": ctx})
            self.context = ctx

    def js(self, script, *args, ctx="chrome"):
        """Execute script (may return a Promise) and return its value."""
        self.set_context(ctx)
        r = self.send("WebDriver:ExecuteScript", {"script": script, "args": list(args)})
        return r.get("value") if isinstance(r, dict) else r

    def navigate(self, url):
        self.set_context("content")
        return self.send("WebDriver:Navigate", {"url": url})

    def quit(self):
        try:
            self.send("Marionette:Quit", {"flags": ["eForceQuit"]})
        except Exception:
            pass


def make_profile(name, extra_prefs=None, fresh=True):
    prof = os.path.join(paths.PROFILES, name)
    if fresh and os.path.isdir(prof):
        shutil.rmtree(prof, ignore_errors=True)
    os.makedirs(prof, exist_ok=True)
    prefs = dict(BASE_PREFS)
    prefs.update(extra_prefs or {})
    with open(os.path.join(prof, "user.js"), "w", encoding="utf-8") as f:
        for k, v in prefs.items():
            f.write(f"user_pref({json.dumps(k)}, {json.dumps(v)});\n")
    return prof


def launch(browser="librewolf", profile_name="lw-test", port=2829, extra_prefs=None,
           fresh=True, exe=None, extra_args=()):
    prefs = {"marionette.port": port}
    prefs.update(extra_prefs or {})
    prof = make_profile(profile_name, prefs, fresh=fresh)
    exe = exe or BROWSERS[browser]
    args = [exe, "-no-remote", "-new-instance", "-profile", prof, "--marionette",
            "--remote-allow-system-access", *extra_args]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    m = Marionette(port)
    m.start_session()
    m.proc = proc
    m.profile = prof
    return m
