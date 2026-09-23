"""Gesture simulation without touching the user's mouse/keyboard.

The module reads modifier/button/cursor through a replaceable 'Native' object;
here it is replaced by a fake controlled from the test, and the window steps a
Windows sizing loop would produce are applied with SetWindowPos (the same
WM_WINDOWPOSCHANGED path Firefox sees during a real drag)."""
import ctypes, json, time
import piptest as pip, winutil as W

SWP = 0x0004 | 0x0010  # NOZORDER | NOACTIVATE

INSTALL_FAKE = """
  const bw = Services.wm.getMostRecentWindow("navigator:browser");
  bw.__fakeNative = { S: { mod: false, button: false, cursor: null, inMove: false },
    modifier() { return this.S.mod; }, primaryButton() { return this.S.button; },
    cursor() { return this.S.cursor; }, inMoveSize() { return this.S.inMove; } };
  PC._setNativeForTests(bw.__fakeNative);
  return 1;"""


class Sim:
    def __init__(self, t, pid):
        self.t, self.pid = t, pid
        t.chrome(INSTALL_FAKE)

    def set(self, **kw):
        self.t.chrome("""Object.assign(Services.wm.getMostRecentWindow("navigator:browser").__fakeNative.S, arguments[0]); return 1;""", kw)

    def state(self):
        return [x for x in self.t.pips() if x["id"] == self.pid][0]["crop"]

    def hwnd(self):
        r = self.state()["rect"]
        return self.t.hwnd_of((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))

    def player(self, method, *args):
        return self.t.player_call(self.pid, method, *args)

    @staticmethod
    def edge_point(r, edges, inset=6):
        x = r["x"] + inset if "l" in edges else r["x"] + r["w"] - 1 - inset if "r" in edges else r["x"] + r["w"] // 2
        y = r["y"] + inset if "t" in edges else r["y"] + r["h"] - 1 - inset if "b" in edges else r["y"] + r["h"] // 2
        return {"x": x, "y": y}

    def gesture(self, edges, dx=0, dy=0, steps=10, modifier=True, pre=True, step_s=0.02, retries=8, trailing=0):
        """edges: subset of 'lrtb' being dragged; dx/dy: total pointer motion.
        The simulation generates no input; it is only invalid if a human touched
        the PiP itself (cursor over it, or the window changed behind our back)."""
        for attempt in range(retries):
            before = self.state()
            ok, st = self._gesture(edges, dx, dy, steps, modifier, pre, step_s, trailing)
            if ok:
                st["interfered"] = attempt
                return st
            print(f"   (PiP touched by the user during gesture {edges}; restoring and retrying)", flush=True)
            time.sleep(2.0)
            self.player("setRect", before["rect"])
            self.t.chrome("""const bw=Services.wm.getMostRecentWindow("navigator:browser");
              const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
              const p=PC.player(w); p.crop = arguments[1]; p.applySteadyLayout(); return 1;""", self.pid, before["crop"])
            time.sleep(0.5)
        raise RuntimeError("could not run gesture without user interference")

    def constraints(self):
        """Window max size (device px) Firefox currently gives Windows' sizing
        loop (real WM_GETMINMAXINFO answer); None where unlimited."""
        t = self.t.chrome("""const w=[...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => w.__testId === arguments[0]);
          return PC.player(w).effectiveMaxTrack();""", self.pid)
        if not t:
            return (None, None)
        return tuple(v if v < (1 << 19) else None for v in (t["x"], t["y"]))

    def _gesture(self, edges, dx, dy, steps, modifier, pre, step_s, trailing=0):
        """Emulates Windows' sizing loop: the size limits are read once when the
        drag starts and the dragged edge is clamped to them; `trailing` extra
        moves are applied after the button is released (queued mouse moves)."""
        h = self.hwnd()
        r = dict(self.state()["rect"])
        ok = True
        def touched(rect):
            cx, cy = W.cursor_pos()
            return rect[0] - 20 <= cx <= rect[2] + 20 and rect[1] - 20 <= cy <= rect[3] + 20
        # hover with the modifier held: the player arms this edge
        self.set(mod=modifier, button=False, inMove=False, cursor=self.edge_point(r, edges))
        time.sleep(0.15 if pre else 0.0)
        maxW, maxH = self.constraints() if pre else (None, None)
        self.set(button=True, inMove=True)
        x0, y0, w0, h0 = r["x"], r["y"], r["w"], r["h"]
        total = steps + trailing
        for i in range(1, total + 1):
            if i == steps + 1:
                self.set(button=False)            # released, loop still draining moves
            ddx, ddy = round(dx * i / steps), round(dy * i / steps)
            x, y, w, hh = x0, y0, w0, h0
            if "l" in edges: x, w = x0 + ddx, w0 - ddx
            if "r" in edges: w = w0 + ddx
            if "t" in edges: y, hh = y0 + ddy, h0 - ddy
            if "b" in edges: hh = h0 + ddy
            if maxW and w > maxW:                 # loop clamps the dragged edge
                if "l" in edges: x = x0 + w0 - maxW
                w = maxW
            if maxH and hh > maxH:
                if "t" in edges: y = y0 + h0 - maxH
                hh = maxH
            ctypes.windll.user32.SetWindowPos(h, 0, x, y, w, hh, SWP)
            got = W.window_rect(h)
            if touched(got):
                ok = False
            self.set(cursor=self.edge_point({"x": got[0], "y": got[1], "w": got[2] - got[0], "h": got[3] - got[1]}, edges))
            time.sleep(step_s)
        self.set(button=False, inMove=False)
        time.sleep(0.35)
        if modifier:
            self.set(mod=False)
        time.sleep(0.3)
        st = self.state()
        rr = st["rect"]
        if touched((rr["x"], rr["y"], rr["x"] + rr["w"], rr["y"] + rr["h"])):
            ok = False
        return ok, st


def report(name, st, shot):
    c = st["crop"]
    s = shot[0]
    v = s.get("verify")
    if v:
        print(f"{name:26s} rect={st['rect']['w']}x{st['rect']['h']}@{st['rect']['x']},{st['rect']['y']} "
              f"crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} | grid X {v['x']['matched']}/{v['x']['expected_lines']} rms {v['x']['rms_px']} "
              f"src {v['x'].get('src0')}..{v['x'].get('src1')} | grid Y {v['y']['matched']}/{v['y']['expected_lines']} rms {v['y']['rms_px']} "
              f"src {v['y'].get('src0')}..{v['y'].get('src1')} | scale {v['x'].get('scale')}/{v['y'].get('scale')} stretch {v.get('stretch')} "
              f"black {v['black_px']} darkEdges {v['edges_dark']} off={s['offscreen_px']} unlocked={st['unlocked']}", flush=True)
        return
    print(f"{name:26s} rect={st['rect']['w']}x{st['rect']['h']}@{st['rect']['x']},{st['rect']['y']} "
          f"crop l={c['l']:.3f} r={c['r']:.3f} t={c['t']:.3f} b={c['b']:.3f} | src={s['src']} "
          f"sx={s['sx']} sy={s['sy']} stretch={s['stretch']} black={s['black_px']} edges={s['edges']} "
          f"off={s['offscreen_px']} unlocked={st['unlocked']} gesture={st['gesture']}", flush=True)
