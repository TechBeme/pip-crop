/* PiP Crop — interactive crop for the native Picture-in-Picture window of
 * Firefox / LibreWolf (tested on 156, Windows 11).
 *
 *   drag an edge or corner          -> normal proportional resize (crop is kept)
 *   Shift + drag an edge or corner  -> crop that side: the window edge moves,
 *                                      the video keeps its on-screen scale;
 *                                      dragging outward uncrops and the edge
 *                                      stops at the edge of the video
 *   Shift + double-click            -> remove the crop
 *
 * Runs in the parent process with chrome privileges (WebExtension Experiment,
 * AutoConfig, or Services.scriptloader.loadSubScript). It only touches the PiP
 * player window (chrome://global/content/pictureinpicture/player.xhtml): the
 * <xul:browser> that shows Firefox's own visual clone of the video is laid out
 * larger than the window and offset, and the compositor clips it. No page
 * script, no canvas and no captureStream, so it also works with cross-origin
 * (no CORS) and DRM video, and costs no extra decoding or copying.
 *
 * Every PiP window gets its own independent crop state.
 */

/* eslint-env mozilla/chrome-script */
/* global Services, ChromeUtils, Ci, Cu, Cc */

var PipCrop = (function () {
  "use strict";

  const PIP_WINDOWTYPE = "Toolkit:PictureInPicture";
  const PIP_MODULES = [
    "moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs",
    "resource://gre/modules/PictureInPicture.sys.mjs",
  ];
  // Must match RESIZE_MARGIN_PX in PictureInPicture.sys.mjs (CSS px).
  const RESIZE_MARGIN_CSS = 16;
  // Never crop a dimension below this fraction of the frame.
  const MIN_FRAC = 0.04;
  // How often the physical modifier and cursor are checked to arm an edge.
  const ARM_POLL_MS = 50;
  const PREF_BRANCH = "extensions.pipcrop.";
  const IS_WIN = Services.appinfo.OS === "WINNT";

  const prefs = {
    get modifier() {
      return Services.prefs.getStringPref(PREF_BRANCH + "modifier", "shift");
    },
    get hint() {
      return Services.prefs.getBoolPref(PREF_BRANCH + "hint", true);
    },
    get debug() {
      return Services.prefs.getBoolPref(PREF_BRANCH + "debug", false);
    },
  };

  // ---------------------------------------------------------------------------
  // Physical keyboard / mouse state (Windows). The native resize border is
  // non-client area: Windows sends no DOM events for it, so the modifier, the
  // button and the cursor are read directly.
  // ---------------------------------------------------------------------------
  let Native = (() => {
    if (!IS_WIN) {
      return null;
    }
    try {
      const { ctypes } = ChromeUtils.importESModule(
        "resource://gre/modules/ctypes.sys.mjs"
      );
      const user32 = ctypes.open("user32.dll");
      const kernel32 = ctypes.open("kernel32.dll");
      const GetAsyncKeyState = user32.declare(
        "GetAsyncKeyState", ctypes.winapi_abi, ctypes.short, ctypes.int
      );
      const GetSystemMetrics = user32.declare(
        "GetSystemMetrics", ctypes.winapi_abi, ctypes.int, ctypes.int
      );
      // Win32 LONG is 32-bit; int32_t also comes back as a plain JS number
      // (js-ctypes returns ctypes.long as an Int64 object).
      const POINT = new ctypes.StructType("POINT", [
        { x: ctypes.int32_t },
        { y: ctypes.int32_t },
      ]);
      const RECT = new ctypes.StructType("RECT", [
        { left: ctypes.int32_t },
        { top: ctypes.int32_t },
        { right: ctypes.int32_t },
        { bottom: ctypes.int32_t },
      ]);
      const GUITHREADINFO = new ctypes.StructType("GUITHREADINFO", [
        { cbSize: ctypes.uint32_t },
        { flags: ctypes.uint32_t },
        { hwndActive: ctypes.voidptr_t },
        { hwndFocus: ctypes.voidptr_t },
        { hwndCapture: ctypes.voidptr_t },
        { hwndMenuOwner: ctypes.voidptr_t },
        { hwndMoveSize: ctypes.voidptr_t },
        { hwndCaret: ctypes.voidptr_t },
        { rcCaret: RECT },
      ]);
      const GetCursorPos = user32.declare(
        "GetCursorPos", ctypes.winapi_abi, ctypes.int, POINT.ptr
      );
      const GetGUIThreadInfo = user32.declare(
        "GetGUIThreadInfo", ctypes.winapi_abi, ctypes.int, ctypes.uint32_t, GUITHREADINFO.ptr
      );
      const GetCurrentThreadId = kernel32.declare(
        "GetCurrentThreadId", ctypes.winapi_abi, ctypes.uint32_t
      );
      const SendMessageW = user32.declare(
        "SendMessageW", ctypes.winapi_abi, ctypes.intptr_t,
        ctypes.voidptr_t, ctypes.uint32_t, ctypes.uintptr_t, ctypes.intptr_t
      );
      const WM_NCHITTEST = 0x84;
      const WM_GETMINMAXINFO = 0x24;
      const MINMAXINFO = new ctypes.StructType("MINMAXINFO", [
        { ptReserved: POINT },
        { ptMaxSize: POINT },
        { ptMaxPosition: POINT },
        { ptMinTrackSize: POINT },
        { ptMaxTrackSize: POINT },
      ]);
      const SendMinMaxInfo = user32.declare(
        "SendMessageW", ctypes.winapi_abi, ctypes.intptr_t,
        ctypes.voidptr_t, ctypes.uint32_t, ctypes.uintptr_t, MINMAXINFO.ptr
      );
      const uiThread = GetCurrentThreadId();
      const GUI_INMOVESIZE = 0x2;
      const down = vk => (GetAsyncKeyState(vk) & 0x8000) !== 0;
      const VK = { shift: 0x10, alt: 0x12 };
      return {
        modifier: () => down(VK[prefs.modifier] || VK.shift),
        // SM_SWAPBUTTON: the primary button is the right one when swapped.
        primaryButton: () => down(GetSystemMetrics(23) ? 0x02 : 0x01),
        cursor() {
          const p = new POINT();
          return GetCursorPos(p.address()) ? { x: p.x, y: p.y } : null;
        },
        // Ask our own window what Windows will do at a screen point (HTLEFT,
        // HTBOTTOMRIGHT, ...). nsWindow answers from geometry only.
        hitTest(hwnd, x, y) {
          const lp = ((y & 0xffff) << 16) | (x & 0xffff);
          return Number(SendMessageW(ctypes.voidptr_t(hwnd), WM_NCHITTEST, 0, lp));
        },
        // The largest window size Firefox would give Windows' sizing loop.
        maxTrack(hwnd) {
          const big = 1 << 20;
          const m = new MINMAXINFO();
          m.ptMaxTrackSize = new POINT(big, big);
          m.ptMaxSize = new POINT(big, big);
          SendMinMaxInfo(ctypes.voidptr_t(hwnd), WM_GETMINMAXINFO, 0, m.address());
          return { x: m.ptMaxTrackSize.x, y: m.ptMaxTrackSize.y };
        },
        // True while Windows runs its modal move/size loop on our UI thread.
        // The loop keeps applying queued mouse moves after the button is
        // released, so a drag only ends when this turns false.
        inMoveSize() {
          const info = new GUITHREADINFO();
          info.cbSize = GUITHREADINFO.size;
          return (
            GetGUIThreadInfo(uiThread, info.address()) !== 0 &&
            (info.flags & GUI_INMOVESIZE) !== 0
          );
        },
      };
    } catch (e) {
      Cu.reportError(e);
      return null;
    }
  })();

  const RealNative = Native;

  function modifierOf(event) {
    return prefs.modifier === "alt" ? event.altKey : event.shiftKey;
  }

  function isModifierKey(event) {
    return prefs.modifier === "alt" ? event.key === "Alt" : event.key === "Shift";
  }

  function sameRect(a, b) {
    return !!a && !!b && a.x === b.x && a.y === b.y && a.w === b.w && a.h === b.h;
  }

  function sameEdges(a, b) {
    return !!a && !!b && a.left === b.left && a.right === b.right &&
      a.top === b.top && a.bottom === b.bottom;
  }

  function setStyles(el, styles) {
    for (const [k, v] of Object.entries(styles)) {
      el.style.setProperty(k, v, "important");
    }
  }

  // WM_NCHITTEST results that start a resize, as the edges they move.
  const HT_EDGES = {
    10: { left: true, right: false, top: false, bottom: false },
    11: { left: false, right: true, top: false, bottom: false },
    12: { left: false, right: false, top: true, bottom: false },
    13: { left: true, right: false, top: true, bottom: false },
    14: { left: false, right: true, top: true, bottom: false },
    15: { left: false, right: false, top: false, bottom: true },
    16: { left: true, right: false, top: false, bottom: true },
    17: { left: false, right: true, top: false, bottom: true },
  };

  const BROWSER_PROPS = [
    "position", "flex", "margin", "width", "height", "left", "top", "right",
    "bottom", "clip-path",
  ];

  // ---------------------------------------------------------------------------
  // One instance per PiP player window.
  // ---------------------------------------------------------------------------
  class CropPlayer {
    constructor(win, aspect) {
      this.win = win;
      this.doc = win.document;
      // Aspect ratio (width / height) of the source video frame.
      this.aspect = aspect > 0 && isFinite(aspect) ? aspect : win.innerWidth / win.innerHeight;
      // Crop as fractions of the source frame, per side.
      this.crop = { l: 0, r: 0, t: 0, b: 0 };
      // Modifier held while the cursor is over this window (drives the hint).
      this.modHeld = false;
      // Aspect-ratio lock released (crop drags resize one dimension only).
      this.unlocked = false;
      // Edges prepared for a crop drag: the modifier is held and the cursor
      // sits on them, so the window size is already capped at the video.
      this.armed = null;
      this.armedRect = null;
      // max-width/max-height currently set on the player's root element.
      this.constrained = false;
      // What Firefox adds when it turns those into window limits (it assumes
      // a default frame the PiP window doesn't have); measured per DPI.
      this.slack = null;
      this.calibrating = false;
      this.needsCalibration = false;
      this.gesture = null;
      this.expect = null;
      this.pollTimer = null;
      this.armTimer = null;
      const owner = win.docShell.treeOwner;
      this.base = owner.QueryInterface(Ci.nsIBaseWindow);
      this.hwnd = parseInt(this.base.nativeHandle, 16) || 0;
      this.app = owner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIAppWindow);
      this.lastRect = this.rect();
      this.debugLog = [];

      this.onEvent = this.onEvent.bind(this);
      for (const t of CropPlayer.EVENTS) {
        win.addEventListener(t, this.onEvent, true);
      }
      win.windowRoot.addEventListener("MozUpdateWindowPos", this.onEvent, true);
      win.addEventListener("unload", () => this.detach(), { once: true });
      // The size limits below are max-width/max-height on the root element,
      // compensated for a frame the PiP window doesn't have, so they can make
      // <html> a little narrower than the window. Size the video's container
      // by the viewport so that never shows.
      setStyles(this.holder, { width: "100vw" });
      if (Native) {
        this.armTimer = win.setInterval(() => this.tick(), ARM_POLL_MS);
      }
      this.calibrate();
    }

    static EVENTS = [
      "keydown", "keyup", "mousemove", "mouseover", "mousedown", "mouseup",
      "dblclick", "blur", "resize", "MozDOMFullscreen:Entered",
      "MozDOMFullscreen:Exited",
    ];

    detach() {
      if (this.win.closed) {
        this.pollTimer = this.armTimer = null;
        return;
      }
      this.win.clearInterval(this.armTimer);
      this.win.clearTimeout(this.pollTimer);
      this.pollTimer = this.armTimer = null;
      for (const t of CropPlayer.EVENTS) {
        this.win.removeEventListener(t, this.onEvent, true);
      }
      this.win.windowRoot?.removeEventListener("MozUpdateWindowPos", this.onEvent, true);
      this.gesture = null;
      this.armed = this.armedRect = null;
      this.clearConstraints();
      this.showHint(false);
      this.setLocked(true);
    }

    trace(...args) {
      if (prefs.debug) {
        this.debugLog.push([Math.round(this.win.performance.now()), ...args]);
        if (this.debugLog.length > 400) {
          this.debugLog.splice(0, 100);
        }
      }
    }

    get holder() {
      return this.doc.querySelector(".player-holder");
    }

    get browser() {
      return this.doc.getElementById("browser");
    }

    hasCrop() {
      const c = this.crop;
      return c.l > 0 || c.r > 0 || c.t > 0 || c.b > 0;
    }

    isFullscreen() {
      return !!this.doc.fullscreenElement || this.win.windowState === this.win.STATE_FULLSCREEN;
    }

    // Window bounds in device pixels (live GetWindowRect).
    rect() {
      const x = {}, y = {}, w = {}, h = {};
      this.base.getPositionAndSize(x, y, w, h);
      return { x: x.value, y: y.value, w: w.value, h: h.value };
    }

    // Atomic move+resize (one SetWindowPos), then re-lock the aspect ratio to
    // the new shape: the 4-argument nsWindow::Resize does not refresh it.
    setRect(r) {
      r = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) };
      this.expect = r;
      this.base.setPositionAndSize(r.x, r.y, r.w, r.h, Ci.nsIBaseWindow.eRepaint);
      const got = this.rect();
      this.trace("setRect", r, got);
      this.lastRect = got;
      if (!this.unlocked) {
        this.app.lockAspectRatio(true);
      }
      return got;
    }

    setLocked(lock) {
      if (lock === !this.unlocked) {
        return;
      }
      try {
        this.app.lockAspectRatio(lock);
      } catch (e) {
        Cu.reportError(e);
      }
      this.unlocked = !lock;
    }

    syncLock() {
      const wantUnlocked =
        !this.isFullscreen() &&
        (!!this.gesture || !!this.armed || (!Native && this.modHeld));
      this.setLocked(!wantUnlocked);
    }

    // Frame (whole source video) rectangle in device px for the current window
    // and crop: the window is an aperture onto this rectangle. The frame's
    // shape always comes from the video's aspect ratio, so integer rounding of
    // window sizes never accumulates into letterbox lines.
    frameFor(rect, crop = this.crop) {
      const cw = 1 - crop.l - crop.r, ch = 1 - crop.t - crop.b;
      let w = rect.w / cw, h = rect.h / ch;
      if (rect.w >= rect.h * this.aspect * (ch / cw)) {
        h = w / this.aspect;
      } else {
        w = h * this.aspect;
      }
      return { x: rect.x - crop.l * w, y: rect.y - crop.t * h, w, h };
    }

    // How big the window may get when these edges move outward: up to the
    // edge of the video frame.
    limitsFor(edges, r, f) {
      return {
        maxW: edges.left ? r.x + r.w - f.x : edges.right ? f.x + f.w - r.x : null,
        maxH: edges.top ? r.y + r.h - f.y : edges.bottom ? f.y + f.h - r.y : null,
      };
    }

    // ---- size constraints ---------------------------------------------------
    // max-width/max-height on the player's root element become the widget's
    // size constraints (PresShell::SyncWindowPropertiesIfNeeded, applied on the
    // next paint) and Firefox answers WM_GETMINMAXINFO with them, so the
    // Windows sizing loop itself stops the dragged edge at the video's edge.
    // A limit below the current size would make Firefox resize the window
    // right away, so `atLeast` keeps it at or above the current size.
    setConstraints(maxW, maxH, atLeast = null) {
      const root = this.doc.documentElement;
      const dpr = this.win.devicePixelRatio;
      let slack = this.slack;
      if (slack && slack.dpr !== dpr) {
        // Moved to a screen with another scale: frame metrics scale with DPI.
        // Use that estimate now and measure again once nothing is armed.
        slack = { w: Math.round((slack.w * dpr) / slack.dpr), h: Math.round((slack.h * dpr) / slack.dpr) };
        this.needsCalibration = true;
      } else if (!slack) {
        this.needsCalibration = true;
      }
      const css = (v, cur, extra) =>
        v == null
          ? null
          : `${Math.max(Math.floor(v + 0.001) - extra, (cur ?? 0) - extra, 1) / dpr}px`;
      const w = css(maxW, atLeast?.w, slack?.w ?? 0);
      const h = css(maxH, atLeast?.h, slack?.h ?? 0);
      for (const [prop, v] of [["max-width", w], ["max-height", h]]) {
        if (v == null) {
          root.style.removeProperty(prop);
        } else {
          root.style.setProperty(prop, v, "important");
        }
      }
      this.constrained = w != null || h != null;
    }

    // Measure the slack with a probe limit larger than the window (so nothing
    // resizes), once the next paint has handed it to the widget.
    calibrate() {
      if (!RealNative?.maxTrack || !this.hwnd || this.calibrating || this.constrained) {
        return;
      }
      const root = this.doc.documentElement;
      const dpr = this.win.devicePixelRatio;
      const r = this.rect();
      const probe = { w: r.w + 400, h: r.h + 400 };
      this.calibrating = true;
      root.style.setProperty("max-width", `${probe.w / dpr}px`, "important");
      root.style.setProperty("max-height", `${probe.h / dpr}px`, "important");
      this.win.requestAnimationFrame(() =>
        this.win.setTimeout(() => {
          this.calibrating = false;
          if (this.win.closed) {
            return;
          }
          const t = RealNative.maxTrack(this.hwnd);
          if (!this.constrained) {
            root.style.removeProperty("max-width");
            root.style.removeProperty("max-height");
          }
          if (t.x < 1 << 19 && t.y < 1 << 19) {
            this.slack = { w: t.x - probe.w, h: t.y - probe.h, dpr };
            this.needsCalibration = false;
          }
          this.trace("calibrated", this.slack, t, probe);
        }, 0)
      );
    }

    // The limit Firefox is currently giving Windows (tests/diagnostics).
    effectiveMaxTrack() {
      return RealNative?.maxTrack && this.hwnd ? RealNative.maxTrack(this.hwnd) : null;
    }

    clearConstraints() {
      if (!this.constrained) {
        return;
      }
      const root = this.doc.documentElement;
      root.style.removeProperty("max-width");
      root.style.removeProperty("max-height");
      this.constrained = false;
    }

    // ---- layout -----------------------------------------------------------

    clearLayout() {
      const br = this.browser;
      if (br) {
        for (const p of BROWSER_PROPS) {
          br.style.removeProperty(p);
        }
      }
      this.holder?.style.removeProperty("position");
    }

    // Undo everything this module put in the player document.
    restoreDocument() {
      this.clearLayout();
      this.clearConstraints();
      this.holder?.style.removeProperty("width");
      this.doc.getElementById("pipcrop-hint")?.remove();
    }

    // Percent layout: exact for any window size with the crop's aspect ratio,
    // so native proportional resizing needs no script at all.
    applySteadyLayout() {
      if (this.gesture) {
        return;
      }
      if (!this.hasCrop()) {
        this.clearLayout();
        return;
      }
      if (this.isFullscreen()) {
        this.applyFullscreenLayout();
        return;
      }
      const { l, r, t, b } = this.crop;
      const cw = 1 - l - r, ch = 1 - t - b;
      setStyles(this.holder, { position: "relative" });
      setStyles(this.browser, {
        position: "absolute", flex: "none", margin: "0", "clip-path": "none",
        width: `${100 / cw}%`, height: `${100 / ch}%`,
        left: `${(-100 * l) / cw}%`, top: `${(-100 * t) / ch}%`,
        right: "auto", bottom: "auto",
      });
    }

    // Fullscreen: letterbox the cropped region inside the screen and clip the
    // rest of the frame.
    applyFullscreenLayout() {
      const holder = this.holder;
      const Hw = holder.clientWidth, Hh = holder.clientHeight;
      const { l, r, t, b } = this.crop;
      const cw = 1 - l - r, ch = 1 - t - b;
      const regionAspect = (this.aspect * cw) / ch;
      let rw, rh;
      if (Hw / Hh > regionAspect) {
        rh = Hh;
        rw = rh * regionAspect;
      } else {
        rw = Hw;
        rh = rw / regionAspect;
      }
      const Fw = rw / cw, Fh = rh / ch;
      const ox = (Hw - rw) / 2, oy = (Hh - rh) / 2;
      setStyles(holder, { position: "relative" });
      setStyles(this.browser, {
        position: "absolute", flex: "none", margin: "0",
        width: `${Fw}px`, height: `${Fh}px`,
        left: `${ox - l * Fw}px`, top: `${oy - t * Fh}px`, right: "auto", bottom: "auto",
        "clip-path": `inset(${t * Fh}px ${r * Fw}px ${b * Fh}px ${l * Fw}px)`,
      });
    }

    // During a crop drag the frame stays still on screen and the window moves
    // over it. The browser is anchored to the window edges that do not move,
    // so the compositor keeps the frame steady without per-frame script.
    applyAnchoredLayout({ start: s, frame: f, edges }) {
      const dpr = this.win.devicePixelRatio;
      const st = {
        position: "absolute", flex: "none", margin: "0", "clip-path": "none",
        width: `${f.w / dpr}px`, height: `${f.h / dpr}px`,
      };
      if (edges.left && !edges.right) {
        st.left = "auto";
        st.right = `${(s.x + s.w - (f.x + f.w)) / dpr}px`;
      } else {
        st.right = "auto";
        st.left = `${(f.x - s.x) / dpr}px`;
      }
      if (edges.top && !edges.bottom) {
        st.top = "auto";
        st.bottom = `${(s.y + s.h - (f.y + f.h)) / dpr}px`;
      } else {
        st.bottom = "auto";
        st.top = `${(f.y - s.y) / dpr}px`;
      }
      setStyles(this.holder, { position: "relative" });
      setStyles(this.browser, st);
    }

    showHint(on) {
      let el = this.doc.getElementById("pipcrop-hint");
      if (!on || !prefs.hint) {
        if (el) {
          el.hidden = true;
        }
        return;
      }
      if (!el) {
        el = this.doc.createElement("div");
        el.id = "pipcrop-hint";
        setStyles(el, {
          position: "fixed", inset: "0", "pointer-events": "none", "z-index": "2147483647",
          "box-shadow": "inset 0 0 0 2px rgba(255,255,255,0.75), inset 0 0 0 3px rgba(0,0,0,0.45)",
        });
        this.doc.body.appendChild(el);
      }
      el.hidden = false;
    }

    // ---- arming (Windows) ---------------------------------------------------

    // Runs every ARM_POLL_MS: while the modifier is held and the cursor sits on
    // an edge, cap the window at the video and release the aspect lock before
    // the button goes down, because Windows reads the size limits once, when
    // its sizing loop starts.
    tick() {
      if (this.win.closed || this.gesture || this.calibrating) {
        return;
      }
      if (this.isFullscreen()) {
        if (this.armed) {
          this.disarm();
        }
        this.setHover(false);
        return;
      }
      const mod = Native.modifier();
      let over = false;
      let edges = null;
      if (mod) {
        const pt = Native.cursor();
        if (pt) {
          const r = this.rect();
          over = pt.x >= r.x && pt.x < r.x + r.w && pt.y >= r.y && pt.y < r.y + r.h;
          if (over) {
            // With the button down a drag is starting: keep what was armed.
            edges = Native.primaryButton() ? this.armed : this.edgesUnder(pt, r);
          }
        }
      }
      if (edges) {
        this.arm(edges);
      } else if (this.armed) {
        this.disarm();
      }
      this.setHover(mod && over);
    }

    arm(edges) {
      const r = this.rect();
      if (sameEdges(edges, this.armed) && sameRect(r, this.armedRect)) {
        return;
      }
      const f = this.frameFor(r);
      this.armed = edges;
      this.armedRect = r;
      this.trace("arm", edges, r);
      this.syncLock();
      const { maxW, maxH } = this.limitsFor(edges, r, f);
      this.setConstraints(maxW, maxH, r);
      this.applyAnchoredLayout({ start: r, frame: f, edges });
    }

    disarm() {
      this.trace("disarm");
      this.armed = this.armedRect = null;
      this.clearConstraints();
      this.applySteadyLayout();
      this.syncLock();
      if (this.needsCalibration) {
        this.win.setTimeout(() => this.calibrate(), 0);
      }
    }

    setHover(on) {
      if (on === this.modHeld) {
        return;
      }
      this.modHeld = on;
      this.showHint(on || !!this.gesture);
    }

    // DOM-only fallback when js-ctypes is unavailable.
    setModifier(held) {
      if (held === this.modHeld) {
        return;
      }
      this.modHeld = held;
      this.syncLock();
      this.showHint(held || !!this.gesture);
    }

    // ---- events -----------------------------------------------------------

    onEvent(e) {
      switch (e.type) {
        case "keydown":
        case "keyup":
          if (isModifierKey(e)) {
            if (Native) {
              this.tick();
            } else {
              this.setModifier(e.type === "keydown");
            }
          }
          break;
        case "mousemove":
        case "mouseover":
        case "mousedown":
        case "mouseup":
          if (Native) {
            this.tick();
          } else {
            if (modifierOf(e) !== this.modHeld) {
              this.setModifier(modifierOf(e));
            }
            if (this.gesture) {
              this.finishGesture();
            }
          }
          if (e.type === "mouseup") {
            // A window drag just ended (and Ctrl-snapping may move it next).
            this.win.setTimeout(() => this.refreshLastRect(), 50);
          }
          break;
        case "dblclick":
          if (modifierOf(e) && this.hasCrop()) {
            e.stopImmediatePropagation();
            e.preventDefault();
            this.resetCrop();
          }
          break;
        case "blur":
          if (!Native) {
            this.setModifier(false);
          }
          break;
        case "MozUpdateWindowPos":
          this.onGeometry("move");
          break;
        case "resize":
          this.onGeometry("resize");
          break;
        case "MozDOMFullscreen:Entered":
        case "MozDOMFullscreen:Exited":
          this.gesture = null;
          this.armed = this.armedRect = null;
          this.clearConstraints();
          this.syncLock();
          this.win.requestAnimationFrame(() => this.applySteadyLayout());
          break;
      }
    }

    refreshLastRect() {
      if (!this.gesture && !this.win.closed) {
        this.lastRect = this.rect();
      }
    }

    onGeometry(source) {
      if (this.win.closed) {
        return;
      }
      const cur = this.rect();
      this.trace("geom", source, cur, this.lastRect, !!this.gesture, this.expect);
      if (this.expect) {
        if (sameRect(cur, this.expect)) {
          this.expect = null;
          this.lastRect = cur;
          this.applySteadyLayout();
          return;
        }
        this.expect = null;
      }
      if (this.gesture) {
        this.gesture.last = cur;
        return;
      }
      if (this.isFullscreen()) {
        if (source === "resize") {
          this.applySteadyLayout();
        }
        return;
      }
      const last = this.lastRect;
      const sizeChanged = !last || cur.w !== last.w || cur.h !== last.h;
      const modifier = Native ? Native.modifier() : this.modHeld;
      const dragging = Native ? Native.primaryButton() || !!Native.inMoveSize?.() : true;
      this.trace("geom-decide", { sizeChanged, modifier, dragging, armed: this.armed, unlocked: this.unlocked });
      if (sizeChanged && last && dragging && (modifier || this.armed)) {
        this.beginGesture(last, cur);
        return;
      }
      if (sizeChanged && this.unlocked && !modifier && !this.armed) {
        // A normal resize started while the aspect was still unlocked.
        // Restore the shape and re-lock so the native loop continues
        // proportionally.
        this.modHeld = false;
        this.showHint(false);
        this.setLocked(true);
        const aspect = last.w / last.h;
        const fixed = { ...cur, h: Math.round(cur.w / aspect) };
        if (cur.y !== last.y) {
          fixed.y = cur.y + cur.h - fixed.h;
        }
        this.setRect(fixed);
        this.app.lockAspectRatio(true);
        return;
      }
      this.lastRect = cur;
    }

    // Edges Windows would resize from this point: asked to the window itself
    // when possible, otherwise computed like nsWindow's hit test.
    edgesUnder(pt, rect) {
      // Window geometry queries always go to the real OS (only input state
      // can be replaced for tests).
      if (RealNative?.hitTest && this.hwnd) {
        const e = HT_EDGES[RealNative.hitTest(this.hwnd, pt.x, pt.y)];
        return e ? { ...e } : null;
      }
      return this.edgesAt(pt, rect);
    }

    // Which edges the user grabbed: same test as nsWindow's hit test, applied
    // to the cursor against the current window (the grabbed edge follows it).
    edgesAt(pt, rect) {
      const m = Math.max(1, Math.round(RESIZE_MARGIN_CSS * this.win.devicePixelRatio));
      const top = pt.y >= rect.y && pt.y < rect.y + m;
      const bottom = !top && pt.y < rect.y + rect.h && pt.y >= rect.y + rect.h - m;
      const k = top || bottom ? 2 : 1;
      const left = pt.x >= rect.x && pt.x < rect.x + k * m;
      const right = !left && pt.x < rect.x + rect.w && pt.x >= rect.x + rect.w - k * m;
      return left || right || top || bottom ? { left, right, top, bottom } : null;
    }

    edgesFromDelta(a, b) {
      return {
        left: a.x !== b.x,
        right: a.x + a.w !== b.x + b.w,
        top: a.y !== b.y,
        bottom: a.y + a.h !== b.y + b.h,
      };
    }

    beginGesture(start, cur) {
      const armed = sameRect(start, this.armedRect) ? this.armed : null;
      const pt = Native?.cursor();
      const edges = armed || (pt && this.edgesUnder(pt, cur)) || this.edgesFromDelta(start, cur);
      const frame = this.frameFor(start);
      this.gesture = { start, edges, frame, last: cur, armed: !!armed };
      this.armed = this.armedRect = null;
      this.trace("begin", { start, cur, pt, edges, frame, armed: !!armed, crop: { ...this.crop } });
      if (!armed) {
        // The modifier came too late to arm (the sizing loop already has its
        // limits). Unlock on the next turn of the event loop — nsWindow may
        // just have queued an EnforceAspectRatio runnable that divides by the
        // ratio — and cap the right/bottom edges now: Firefox clamps a
        // too-large window by keeping its top-left corner, which is right for
        // those edges only. Left/top overshoot is undone in finishGesture.
        Services.tm.dispatchToMainThread(() => {
          if (this.gesture && !this.win.closed) {
            this.syncLock();
          }
        });
        const { maxW, maxH } = this.limitsFor({ right: edges.right, bottom: edges.bottom }, start, frame);
        if (maxW != null || maxH != null) {
          this.setConstraints(maxW, maxH);
        }
      }
      this.applyAnchoredLayout(this.gesture);
      this.showHint(true);
      this.pollGestureEnd();
    }

    pollGestureEnd() {
      this.win.clearTimeout(this.pollTimer);
      if (!Native) {
        // Without native state, end after a short quiet period.
        this.pollTimer = this.win.setTimeout(() => this.finishGesture(), 400);
        return;
      }
      const tick = () => {
        this.pollTimer = null;
        if (!this.gesture || this.win.closed) {
          return;
        }
        if (Native.primaryButton() || Native.inMoveSize?.()) {
          this.pollTimer = this.win.setTimeout(tick, 16);
        } else {
          this.finishGesture();
        }
      };
      this.pollTimer = this.win.setTimeout(tick, 16);
    }

    finishGesture() {
      const g = this.gesture;
      if (!g) {
        return;
      }
      this.gesture = null;
      this.clearConstraints();
      const cur = this.rect();
      const f = g.frame;
      // Grabbed edges come from the window, the others stay where they were.
      let L = g.edges.left ? cur.x : g.start.x;
      let R = g.edges.right ? cur.x + cur.w : g.start.x + g.start.w;
      let T = g.edges.top ? cur.y : g.start.y;
      let B = g.edges.bottom ? cur.y + cur.h : g.start.y + g.start.h;
      // Cannot uncrop past the video frame.
      L = Math.max(L, Math.round(f.x));
      T = Math.max(T, Math.round(f.y));
      R = Math.min(R, Math.round(f.x + f.w));
      B = Math.min(B, Math.round(f.y + f.h));
      // Keep a minimum visible part of the frame.
      const minW = Math.max(MIN_FRAC * f.w, 32), minH = Math.max(MIN_FRAC * f.h, 32);
      if (R - L < minW) {
        if (g.edges.left) {
          L = R - minW;
        } else {
          R = L + minW;
        }
      }
      if (B - T < minH) {
        if (g.edges.top) {
          T = B - minH;
        } else {
          B = T + minH;
        }
      }
      this.trace("finish", { cur, L, R, T, B, edges: g.edges, frame: f });
      this.syncLock();
      const got = this.setRect({ x: L, y: T, w: R - L, h: B - T });
      // Windows may clamp the size (minimum track size): derive the crop from
      // what the window really is, intersected with the frame.
      this.crop = this.cropFromAperture(got, f);
      this.applySteadyLayout();
      this.showHint(this.modHeld);
      if (Native) {
        // Still holding the modifier on an edge: arm again for the next drag.
        this.tick();
      }
    }

    cropFromAperture(r, f) {
      const snap = v => (v < 0.0015 ? 0 : v);
      return {
        l: snap(Math.max(0, (r.x - f.x) / f.w)),
        r: snap(Math.max(0, (f.x + f.w - (r.x + r.w)) / f.w)),
        t: snap(Math.max(0, (r.y - f.y) / f.h)),
        b: snap(Math.max(0, (f.y + f.h - (r.y + r.h)) / f.h)),
      };
    }

    // ---- programmatic API ---------------------------------------------------

    // New crop keeping the on-screen scale; the frame stays in place.
    setCrop(crop) {
      const c = {
        l: Math.max(0, crop.l ?? this.crop.l), r: Math.max(0, crop.r ?? this.crop.r),
        t: Math.max(0, crop.t ?? this.crop.t), b: Math.max(0, crop.b ?? this.crop.b),
      };
      if (1 - c.l - c.r < MIN_FRAC || 1 - c.t - c.b < MIN_FRAC) {
        throw new Error("crop leaves less than the minimum visible area");
      }
      if (this.isFullscreen()) {
        this.crop = c;
        this.applySteadyLayout();
        return this.status();
      }
      if (this.constrained) {
        // Size limits only leave the widget on the next paint: lift them and
        // resize after it, or the new size would be clamped.
        this.armed = this.armedRect = null;
        this.clearConstraints();
        return new Promise(resolve => {
          this.win.requestAnimationFrame(() =>
            this.win.setTimeout(() => resolve(this.setCrop(c)), 0)
          );
        });
      }
      const f = this.frameFor(this.rect());
      const want = {
        x: f.x + c.l * f.w, y: f.y + c.t * f.h,
        w: f.w * (1 - c.l - c.r), h: f.h * (1 - c.t - c.b),
      };
      const got = this.setRect(this.keepOnScreen(want));
      this.crop = this.cropFromAperture(got, { ...f, x: f.x + (got.x - want.x), y: f.y + (got.y - want.y) });
      this.applySteadyLayout();
      return this.status();
    }

    resetCrop() {
      return this.setCrop({ l: 0, r: 0, t: 0, b: 0 });
    }

    // Slide a rect so it stays inside the available area of its screen.
    keepOnScreen(r) {
      try {
        const sm = Cc["@mozilla.org/gfx/screenmanager;1"].getService(Ci.nsIScreenManager);
        const s = sm.screenForRect(r.x, r.y, r.w, r.h);
        const x = {}, y = {}, w = {}, h = {};
        s.GetAvailRect(x, y, w, h);
        const out = { ...r };
        out.x = Math.min(Math.max(out.x, x.value), x.value + w.value - out.w);
        out.y = Math.min(Math.max(out.y, y.value), y.value + h.value - out.h);
        return out;
      } catch (e) {
        return r;
      }
    }

    status() {
      return {
        crop: { ...this.crop },
        aspect: this.aspect,
        rect: this.rect(),
        unlocked: this.unlocked,
        gesture: !!this.gesture,
        armed: this.armed ? { ...this.armed } : null,
        slack: this.slack,
        constraints: this.constrained
          ? {
              maxWidth: this.doc.documentElement.style.getPropertyValue("max-width"),
              maxHeight: this.doc.documentElement.style.getPropertyValue("max-height"),
            }
          : null,
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Installation: hook PictureInPicture so every new player window is attached
  // and video size changes use the cropped dimensions.
  // ---------------------------------------------------------------------------
  const players = new WeakMap();
  let PiP = null;
  let saved = null;

  function loadPiPModule() {
    for (const url of PIP_MODULES) {
      try {
        return ChromeUtils.importESModule(url).PictureInPicture;
      } catch (e) {
        // try the next location
      }
    }
    throw new Error("PipCrop: PictureInPicture module not found");
  }

  function attach(win, aspect) {
    if (players.has(win)) {
      return players.get(win);
    }
    const p = new CropPlayer(win, aspect);
    players.set(win, p);
    win.addEventListener("unload", () => players.delete(win), { once: true });
    return p;
  }

  function* pipWindows() {
    yield* Services.wm.getEnumerator(PIP_WINDOWTYPE);
  }

  function install() {
    if (saved) {
      return;
    }
    PiP = loadPiPModule();
    if (PiP.__pipcrop && PiP.__pipcrop !== api) {
      // Another copy is already active (the extension and AutoConfig both
      // installed, or two builds): two copies would fight over every window.
      Cu.reportError(
        `PiP Crop ${api.version}: version ${PiP.__pipcrop.version} is already active, not installing twice.`
      );
      return;
    }
    saved = {
      openPipWindow: PiP.openPipWindow,
      resizePictureInPictureWindow: PiP.resizePictureInPictureWindow,
    };
    PiP.openPipWindow = async function (parentWin, videoData) {
      const win = await saved.openPipWindow.call(this, parentWin, videoData);
      try {
        attach(win, videoData.videoWidth / videoData.videoHeight);
      } catch (e) {
        Cu.reportError(e);
      }
      return win;
    };
    PiP.resizePictureInPictureWindow = function (videoData, actorRef) {
      const win = this.getWeakPipPlayer(actorRef);
      const p = win && players.get(win);
      p?.trace("pip-resize", { w: videoData.videoWidth, h: videoData.videoHeight });
      if (p) {
        const a = videoData.videoWidth / videoData.videoHeight;
        if (a > 0 && isFinite(a)) {
          p.aspect = a;
        }
        if (p.hasCrop()) {
          const { l, r, t, b } = p.crop;
          videoData = {
            ...videoData,
            videoWidth: videoData.videoWidth * (1 - l - r),
            videoHeight: videoData.videoHeight * (1 - t - b),
          };
        }
      }
      return saved.resizePictureInPictureWindow.call(this, videoData, actorRef);
    };
    for (const win of pipWindows()) {
      attach(win, 0);
    }
    // Diagnostic handle (Browser Console):
    // ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture.__pipcrop
    PiP.__pipcrop = api;
  }

  function uninstall() {
    if (!saved) {
      return;
    }
    PiP.openPipWindow = saved.openPipWindow;
    PiP.resizePictureInPictureWindow = saved.resizePictureInPictureWindow;
    if (PiP.__pipcrop === api) {
      delete PiP.__pipcrop;
    }
    saved = null;
    for (const win of pipWindows()) {
      const p = players.get(win);
      if (p) {
        p.detach();
        if (p.hasCrop()) {
          try {
            p.resetCrop();
          } catch (e) {
            Cu.reportError(e);
          }
        }
        p.restoreDocument();
        players.delete(win);
      }
    }
  }

  const api = {
    version: "1.3.0",
    install,
    uninstall,
    get installed() {
      return !!saved;
    },
    player(win) {
      return players.get(win) || null;
    },
    get native() {
      return !!Native;
    },
    // Test hook: replace the physical keyboard/mouse reader (null = real one).
    _setNativeForTests(fake) {
      Native = fake || RealNative;
    },
  };
  return api;
})();
