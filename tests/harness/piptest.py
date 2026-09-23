"""Test helpers on top of the Marionette client."""
import json, os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn, winutil, analyze, paths

HERE = str(paths.HARNESS)
OUT = str(paths.OUT)
SHOTS = str(paths.SHOTS)
MODULE = paths.MODULE_URL


class T:
    def __init__(self, port=None):
        port = port or int(os.environ.get("PIPCROP_PORT", "2829"))
        self.m = mn.Marionette(port)
        self.m.start_session()

    PRELUDE = ('const PC = ChromeUtils.importESModule("moz-src:///toolkit/components/'
               'pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture.__pipcrop;\n')

    def chrome(self, code, *args):
        return self.m.js("return (async () => {\n" + self.PRELUDE + code + "\n})();", *args, ctx="chrome")

    def content(self, code, *args):
        return self.m.js("return (async () => {\n" + code + "\n})();", *args, ctx="content")

    def close(self):
        try:
            self.m.send("WebDriver:DeleteSession")
        finally:
            self.m.sock.close()

    # --- browser helpers ---------------------------------------------------
    def status(self):
        return self.chrome("return PC ? { version: PC.version, installed: PC.installed, native: PC.native } : null;")

    def install(self, url=MODULE):
        """Inject src/pipcrop.js, replacing the active copy. With
        PIPCROP_NO_INJECT=1, test the copy the browser already runs instead
        (the installed extension or AutoConfig)."""
        if os.environ.get("PIPCROP_NO_INJECT"):
            return self.status()
        return self.chrome("""
          const bw = Services.wm.getMostRecentWindow("navigator:browser");
          if (PC && PC.installed) PC.uninstall();
          Services.scriptloader.loadSubScriptWithOptions(arguments[0] + "?" + Date.now(), { target: bw, allowUnsafeURL: true });
          bw.PipCrop.install();
          const P2 = ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture.__pipcrop;
          return { version: P2.version, native: P2.native, installed: P2.installed };
        """, url)

    def close_all(self):
        return self.chrome("""
          const wins = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")];
          for (const w of wins) w.close();
          for (let i = 0; i < 30 && [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].length; i++)
            await new Promise(r => setTimeout(r, 100));
          return wins.length;""")

    def new_tab(self, url):
        h = self.m.send("WebDriver:NewWindow", {"type": "tab", "focus": True})["handle"]
        self.m.send("WebDriver:SwitchToWindow", {"handle": h, "focus": True})
        self.m.navigate(url)
        return h

    def open_pip(self, wait=1.2):
        """Native PiP for the playing video of the selected tab (Ctrl+Shift+] path)."""
        r = self.chrome("""
          const bw = Services.wm.getMostRecentWindow("navigator:browser");
          const before = new Set([...Services.wm.getEnumerator("Toolkit:PictureInPicture")]);
          bw.gBrowser.selectedBrowser.browsingContext.currentWindowGlobal
            .getActor("PictureInPictureLauncher").sendAsyncMessage("PictureInPicture:KeyToggle");
          let win = null;
          for (let i = 0; i < 100 && !win; i++) {
            await new Promise(r => setTimeout(r, 100));
            win = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => !before.has(w)) || null;
          }
          if (!win) return null;
          win.__testId = (bw.__pipTestSeq = (bw.__pipTestSeq || 0) + 1);
          return win.__testId;""")
        time.sleep(wait)
        return r

    def pips(self):
        return self.chrome("""
          const bw = Services.wm.getMostRecentWindow("navigator:browser");
          return [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].map(w => {
            const p = PC && PC.player(w);
            return { id: w.__testId, css: [w.screenX, w.screenY, w.innerWidth, w.innerHeight],
                     dpr: w.devicePixelRatio, crop: p ? p.status() : null };
          });""")

    def player_call(self, pid, method, *args):
        return self.chrome("""
          const bw = Services.wm.getMostRecentWindow("navigator:browser");
          const w = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
          const p = PC.player(w);
          const r = p[arguments[1]](...arguments[2]);
          await new Promise(r => setTimeout(r, 400));
          return r === undefined ? p.status() : r;""", pid, method, list(args))

    def wait_controls_hidden(self, timeout=6.0):
        """Native PiP controls fade in on hover; wait until none is showing."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            vis = self.chrome("""return [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].some(w => {
              const c = w.document.getElementById("controls");
              return c.hasAttribute("showing") || c.hasAttribute("keying") || w.document.querySelector("#controls:hover") != null; });""")
            if not vis:
                return True
            time.sleep(0.4)
        return False

    def hwnd_of(self, rect):
        for x in winutil.windows():
            if x["cls"] == "MozillaDialogClass" and x["title"] == "Picture-in-Picture" and x["rect"] == tuple(rect):
                return x["hwnd"]
        return None


def occluded(p):
    h = p.get("hwnd")
    if not h:
        return True
    l, t, r, b = p["rect"]
    for fx in (0.02, 0.5, 0.98):
        for fy in (0.03, 0.5, 0.97):
            x, y = int(l + (r - l) * fx), int(t + (b - t) * fy)
            if winutil.root_of(winutil.window_from_point(x, y)) != h:
                return True
    return False


def shot(name, W=1920, H=1080, calib="native", rect=None, save=True, crop=None):
    """Screenshot PiP windows (or one rect) and measure them."""
    cf = os.path.join(OUT, f"calib_{calib}.json")
    c = tuple(json.load(open(cf))) if os.path.exists(cf) else None
    wins = [x for x in winutil.windows() if x["cls"] == "MozillaDialogClass" and x["title"] == "Picture-in-Picture"]
    if rect:
        # only a PiP window that really is at this rect: never capture a bare
        # screen region (it could be anything the user has open)
        wins = [x for x in wins if x["rect"] == tuple(rect)]
        if not wins:
            return [{"rect": tuple(rect), "missing": True}]
    out = []
    mons = winutil.monitors()
    for i, p in enumerate(sorted(wins, key=lambda x: x["rect"])):
        # never analyze (or keep) pixels of something covering the PiP
        for attempt in range(40):
            if not occluded(p):
                break
            time.sleep(1.5)
        else:
            out.append({"rect": p["rect"], "occluded": True})
            continue
        im = winutil.grab(p["rect"])
        l, tp, rr, bb = p["rect"]
        onscreen = max((max(0, min(rr, m[2]) - max(l, m[0])) * max(0, min(bb, m[3]) - max(tp, m[1])) for m in mons), default=0)
        offscreen = (rr - l) * (bb - tp) - onscreen
        if save:
            im.save(os.path.join(SHOTS, f"{name}_{i}.png"))
        try:
            r = analyze.analyze(im, W, H, c)
        except Exception:
            arr = analyze.np.asarray(im.convert("RGB")).astype("float32")
            r = {"black_px": analyze.black_extent(arr), "edges": analyze.edge_lines(arr),
                 "black": {"any_black_px": float((arr.max(axis=2) < 14).mean())}}
        g = r.get("grid", {})
        out.append({"rect": p["rect"], "win": [p["rect"][2] - p["rect"][0], p["rect"][3] - p["rect"][1]],
                    "black_px": r["black_px"], "edges": r["edges"], "any_black": round(r["black"]["any_black_px"], 4),
                    "src": [g.get("x0"), g.get("x1"), g.get("y0"), g.get("y1")],
                    "sx": g.get("sx"), "sy": g.get("sy"), "stretch": g.get("stretch"), "lines": g.get("lines"),
                    "color_src": [r.get("x0"), r.get("x1"), r.get("y0"), r.get("y1")], "offscreen_px": offscreen})
        if crop is not None:
            out[-1]["verify"] = analyze.verify(im, crop, W, H)
    return out
