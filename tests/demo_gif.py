"""Records docs/images/pip-crop-demo.gif (plus before/after stills): a pillarboxed video in a PiP window, Shift + drag
the left and right edges to crop the black bars off, then a plain corner drag
that resizes and keeps the crop.

Needs the test browser (see README.md) and ffmpeg. Input is simulated, so the
mouse and keyboard are not touched. Only the PiP window's own pixels are
captured, while nothing covers it, and they are composed onto a synthetic
background.

    python tests/demo_gif.py
"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harness")
sys.path.insert(0, HARNESS)
import ctypes, functools, http.server, subprocess, threading, time
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import piptest as pip, winutil as W, paths
from sim import Sim, INSTALL_FAKE, SWP

PORT = 8775
WORK = paths.OUT / "demo"
WORK.mkdir(parents=True, exist_ok=True)
IMAGES = paths.REPO / "docs" / "images"
OUT_GIF = IMAGES / "pip-crop-demo.gif"
BG = (17, 24, 39)
MARGIN = 40


def landscape(w=1280, h=720, bars=160):
    """Flat-color sunset, pillarboxed to 16:9 (the content is 4:3)."""
    cw = w - 2 * bars
    c = Image.new("RGB", (cw, h))
    d = ImageDraw.Draw(c)
    bands = ["#1B1446", "#2E1A5E", "#4B2177", "#7A2D83", "#B8437C", "#EE6A5F", "#F99A57"]
    bh = 430 / len(bands)
    for i, col in enumerate(bands):
        d.rectangle([0, int(i * bh), cw, int((i + 1) * bh) + 1], fill=col)
    sx, sy, sr = int(cw * 0.62), 390, 105
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill="#FFD27A")
    d.polygon([(0, 430), (90, 330), (190, 390), (300, 290), (420, 380), (540, 300), (650, 370),
               (760, 280), (880, 360), (cw, 320), (cw, 470), (0, 470)], fill="#8C3A86")
    d.polygon([(0, 470), (120, 380), (240, 450), (360, 370), (480, 455), (610, 390), (740, 460),
               (860, 400), (cw, 440), (cw, 520), (0, 520)], fill="#56206F")
    d.polygon([(0, 520), (160, 470), (330, 510), (520, 460), (700, 505), (cw, 470), (cw, 540), (0, 540)],
              fill="#2A1147")
    d.rectangle([0, 540, cw, h], fill="#1A0E36")
    for half, y in ((75, 572), (60, 602), (45, 632), (30, 662), (18, 692)):
        d.rounded_rectangle([sx - half, y, sx + half, y + 8], radius=4, fill="#F5B35E")
    im = Image.new("RGB", (w, h), (0, 0, 0))
    im.paste(c, (bars, 0))
    return im


def make_video():
    png, mp4 = WORK / "demo.png", WORK / "demo.mp4"
    landscape().save(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                    "-t", "30", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-colorspace", "bt709",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", str(mp4)], check=True)
    (WORK / "video.html").write_bytes((paths.WWW / "video.html").read_bytes())


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_cursor(d, x, y, kind, s):
    """Windows-style resize cursor: white arrow with a black outline."""
    L, a, t = 13 * s, 6 * s, 2.2 * s
    if kind == "h":
        pts = [(-L, 0), (-L + a, -a), (-L + a, -t), (L - a, -t), (L - a, -a), (L, 0),
               (L - a, a), (L - a, t), (-L + a, t), (-L + a, a)]
    else:  # diagonal, for the bottom-right corner
        k = 0.7071
        base = [(-L, 0), (-L + a, -a), (-L + a, -t), (L - a, -t), (L - a, -a), (L, 0),
                (L - a, a), (L - a, t), (-L + a, t), (-L + a, a)]
        pts = [(px * k - py * k, px * k + py * k) for px, py in base]
    poly = [(x + px, y + py) for px, py in pts]
    d.polygon(poly, fill="white", outline="black", width=max(1, round(1.3 * s)))


def draw_shift(d, s):
    x, y = 14 * s, 12 * s
    w, h = 92 * s, 34 * s
    d.rounded_rectangle([x, y, x + w, y + h], radius=7 * s, fill="#F8FAFC", outline="#94A3B8", width=max(1, round(s)))
    ax, ay = x + 16 * s, y + h / 2          # outlined up arrow (the Shift symbol)
    arrow = [(ax, ay - 9 * s), (ax + 9 * s, ay + 1 * s), (ax + 4 * s, ay + 1 * s), (ax + 4 * s, ay + 8 * s),
             (ax - 4 * s, ay + 8 * s), (ax - 4 * s, ay + 1 * s), (ax - 9 * s, ay + 1 * s)]
    d.polygon(arrow, outline="#0F172A", width=max(1, round(1.6 * s)))
    d.text((x + 31 * s, y + h / 2), "Shift", fill="#0F172A", font=font(round(16 * s)), anchor="lm")


def main():
    make_video()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Quiet, directory=str(WORK)))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    t = pip.T()
    t.close_all()
    for _ in range(120):                      # keep the real cursor away from the demo area
        cx, cy = W.cursor_pos()
        if not (0 <= cx < 1100 and 250 <= cy < 1000):
            break
        time.sleep(1.0)
    print("module:", t.install())
    t.chrome(INSTALL_FAKE)
    t.m.navigate(f"http://127.0.0.1:{PORT}/video.html?src=demo.mp4"); time.sleep(1.5)
    pid = t.open_pip(wait=1.0)
    sim = Sim(t, pid)
    dpr = [x for x in t.pips() if x["id"] == pid][0]["dpr"]
    s = dpr
    w0 = round(560 * s)
    h0 = round(w0 * 9 / 16)
    x0, y0 = 80, 360
    sim.player("setRect", {"x": x0, "y": y0, "w": w0, "h": h0})
    time.sleep(2.0)
    t.wait_controls_hidden()
    h = sim.hwnd()
    grow = round(96 * s)
    ox, oy = x0 - round(MARGIN * s), y0 - round(MARGIN * s)
    cw = w0 + 2 * round(MARGIN * s)
    ch = round(h0 * (1 + grow / (w0 * 0.75))) + 2 * round(MARGIN * s)
    radius = round(8 * s)
    frames = []  # (canvas image, duration ms)

    def capture():
        l, tp, r, b = W.window_rect(h)
        for _ in range(20):
            if not pip.occluded({"hwnd": h, "rect": (l, tp, r, b)}) and not covered((l, tp, r, b)):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("the PiP window is covered; not capturing")
        return W.grab((l, tp, r, b)), (l, tp, r, b)

    def covered(rect):
        l, tp, r, b = rect
        for fx in (0.02, 0.25, 0.5, 0.75, 0.98):
            for fy in (0.03, 0.25, 0.5, 0.75, 0.97):
                x, y = int(l + (r - l) * fx), int(tp + (b - tp) * fy)
                if W.root_of(W.window_from_point(x, y)) != h:
                    return True
        return False

    def compose(shot, rect, cursor=None, kind="h", shift=False):
        img, (l, tp, r, b) = shot, rect
        canvas = Image.new("RGB", (cw, ch), BG)
        wx, wy, ww, wh = l - ox, tp - oy, r - l, b - tp
        shadow = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(shadow).rounded_rectangle([wx, wy + 6 * s, wx + ww, wy + wh + 6 * s], radius=radius, fill=150)
        shadow = shadow.filter(ImageFilter.GaussianBlur(10 * s))
        canvas.paste((0, 0, 0), mask=shadow)
        # rounded corners: only the window's own pixels are kept
        mask = Image.new("L", (ww, wh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, ww - 1, wh - 1], radius=radius, fill=255)
        canvas.paste(img, (wx, wy), mask)
        d = ImageDraw.Draw(canvas)
        if shift:
            draw_shift(d, s)
        if cursor:
            draw_cursor(d, cursor[0] - ox, cursor[1] - oy, kind, s)
        return canvas

    def edge_xy(rect, edge):
        l, tp, r, b = rect
        inset = round(4 * s)
        return {"l": (l + inset, (tp + b) // 2), "r": (r - 1 - inset, (tp + b) // 2),
                "rb": (r - 1 - inset, b - 1 - inset)}[edge]

    def add(img, ms):
        frames.append((img, ms))

    def move_cursor(shot, rect, a, b_, kind, shift, n=6, ms=45):
        for i in range(1, n + 1):
            f = i / n
            add(compose(shot, rect, (a[0] + (b_[0] - a[0]) * f, a[1] + (b_[1] - a[1]) * f), kind, shift), ms)

    def drag(edge, dx, steps, shift, kind):
        rect = W.window_rect(h)
        r = {"x": rect[0], "y": rect[1], "w": rect[2] - rect[0], "h": rect[3] - rect[1]}
        sim.set(mod=shift, button=False, inMove=False, cursor=Sim.edge_point(r, edge))
        time.sleep(0.3)
        maxW, _ = sim.constraints() if shift else (None, None)
        sim.set(button=True, inMove=True)
        for i in range(1, steps + 1):
            ddx = round(dx * i / steps)
            x, y, w, hh = r["x"], r["y"], r["w"], r["h"]
            if edge == "l":
                x, w = r["x"] + ddx, r["w"] - ddx
            elif edge == "r":
                w = r["w"] + ddx
            else:  # "rb": proportional, like the aspect-locked sizing loop
                w = r["w"] + ddx
                hh = round(w * r["h"] / r["w"])
            if maxW and w > maxW:
                if edge == "l":
                    x = r["x"] + r["w"] - maxW
                w = maxW
            ctypes.windll.user32.SetWindowPos(h, 0, x, y, w, hh, SWP)
            time.sleep(0.07)
            got = W.window_rect(h)
            sim.set(cursor=Sim.edge_point({"x": got[0], "y": got[1], "w": got[2] - got[0], "h": got[3] - got[1]}, edge))
            shot, rr = capture()
            add(compose(shot, rr, edge_xy(rr, edge), kind, shift), 45)
        sim.set(button=False, inMove=False)
        time.sleep(0.6)

    IMAGES.mkdir(parents=True, exist_ok=True)
    shot, rect = capture()
    add(compose(shot, rect), 1300)
    compose(shot, rect).save(IMAGES / "pip-crop-before.png", optimize=True)
    # Shift over the left edge: the hint outline shows
    sim.set(mod=True, button=False, inMove=False, cursor=Sim.edge_point({"x": rect[0], "y": rect[1], "w": rect[2] - rect[0], "h": rect[3] - rect[1]}, "l"))
    time.sleep(0.5)
    shot, rect = capture()
    add(compose(shot, rect, edge_xy(rect, "l"), "h", True), 700)
    bar = round(w0 * 0.125)
    drag("l", +bar, 22, True, "h")
    shot, rect = capture()
    add(compose(shot, rect, edge_xy(rect, "l"), "h", True), 400)
    move_cursor(shot, rect, edge_xy(rect, "l"), edge_xy(rect, "r"), "h", True)
    sim.set(cursor=Sim.edge_point({"x": rect[0], "y": rect[1], "w": rect[2] - rect[0], "h": rect[3] - rect[1]}, "r"))
    time.sleep(0.4)
    drag("r", -bar, 22, True, "h")
    shot, rect = capture()
    add(compose(shot, rect, edge_xy(rect, "r"), "h", True), 700)
    sim.set(mod=False)
    time.sleep(0.5)
    shot, rect = capture()
    add(compose(shot, rect, edge_xy(rect, "r"), "h", False), 700)
    compose(shot, rect).save(IMAGES / "pip-crop-after.png", optimize=True)
    move_cursor(shot, rect, edge_xy(rect, "r"), edge_xy(rect, "rb"), "d", False, n=5)
    drag("rb", grow, 18, False, "d")
    shot, rect = capture()
    add(compose(shot, rect, edge_xy(rect, "rb"), "d", False), 2200)
    st = sim.state()
    print("final:", st["rect"], {k: round(v, 3) for k, v in st["crop"].items()})
    t.close_all()
    t.close()
    server.shutdown()

    # one palette for the whole animation: flat colors stay flat, frames differ only where something moved
    keys = [frames[i][0] for i in (0, 1, len(frames) // 2, -1)]
    strip = Image.new("RGB", (keys[0].width * len(keys), keys[0].height))
    for i, k in enumerate(keys):
        strip.paste(k, (i * k.width, 0))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    imgs = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f, _ in frames]
    imgs[0].save(OUT_GIF, save_all=True, append_images=imgs[1:], duration=[ms for _, ms in frames],
                 loop=0, optimize=False, disposal=1)
    sheet_w = 6
    thumbs = [f.resize((f.width // 3, f.height // 3)) for f, _ in frames]
    sheet = Image.new("RGB", (thumbs[0].width * sheet_w, thumbs[0].height * ((len(thumbs) + sheet_w - 1) // sheet_w)), "white")
    for i, th in enumerate(thumbs):
        sheet.paste(th, ((i % sheet_w) * th.width, (i // sheet_w) * th.height))
    sheet.save(paths.SHOTS / "demo_contact_sheet.png")
    print(f"wrote {OUT_GIF} ({OUT_GIF.stat().st_size} bytes, {len(frames)} frames, {cw}x{ch})")


if __name__ == "__main__":
    main()
