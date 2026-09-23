"""Records docs/images/pip-crop-multiple-windows.png: three PiP windows at once,
each cropped differently (a pillarboxed 4:3 picture, a letterboxed 2.39:1
film and a vertical video in a 16:9 frame).

Needs the test browser (see README.md) and ffmpeg. Only the PiP windows' own
pixels are captured, while nothing covers them, and they are composed onto a
synthetic background.

    python tests/screenshots.py
"""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harness")
sys.path.insert(0, HARNESS)
import functools, http.server, subprocess, threading, time
from PIL import Image, ImageDraw, ImageFilter
import piptest as pip, winutil as W, paths
from demo_gif import landscape, Quiet

PORT = 8776
WORK = paths.OUT / "screenshots"
WORK.mkdir(parents=True, exist_ok=True)
OUT = paths.REPO / "docs" / "images" / "pip-crop-multiple-windows.png"
BG = (17, 24, 39)


def desert(w=1280, h=720, content_h=536):
    """Flat-color desert road at dusk, letterboxed (2.39:1 in 16:9)."""
    c = Image.new("RGB", (w, content_h))
    d = ImageDraw.Draw(c)
    bands = ["#0F3D4C", "#15596A", "#227A86", "#43A0A0", "#8CC6B4", "#F2D7A4", "#F7B77A"]
    horizon = 300
    bh = horizon / len(bands)
    for i, col in enumerate(bands):
        d.rectangle([0, int(i * bh), w, int((i + 1) * bh) + 1], fill=col)
    d.ellipse([880, 190, 1000, 310], fill="#FFE3A3")
    d.polygon([(0, 300), (160, 250), (330, 285), (520, 235), (700, 280), (900, 240), (1100, 275), (w, 250), (w, content_h), (0, content_h)], fill="#C9804E")
    d.polygon([(0, 360), (260, 320), (560, 350), (880, 315), (w, 345), (w, content_h), (0, content_h)], fill="#A55E36")
    d.polygon([(560, 300), (720, 300), (1040, content_h), (240, content_h)], fill="#3B2C35")
    for y0, y1, half in ((330, 350, 3), (375, 405, 5), (430, 475, 8), (500, content_h, 12)):
        d.polygon([(640 - half, y0), (640 + half, y0), (640 + half * 1.4, y1), (640 - half * 1.4, y1)], fill="#F4E3C1")
    im = Image.new("RGB", (w, h), (0, 0, 0))
    im.paste(c, (0, (h - content_h) // 2))
    return im


def city(w=1280, h=720):
    """Flat-color city at night, a vertical 9:16 video pillarboxed in 16:9."""
    cw = round(h * 9 / 16)
    c = Image.new("RGB", (cw, h), "#0B1330")
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, cw, 260], fill="#101C45")
    d.ellipse([260, 70, 330, 140], fill="#F4EFD8")
    for x, y in ((40, 60), (120, 150), (200, 40), (330, 200), (80, 230), (360, 110), (170, 260)):
        d.ellipse([x, y, x + 4, y + 4], fill="#C9D4FF")
    buildings = [(0, 420, 90, "#1F2A5C"), (80, 330, 70, "#26336B"), (145, 470, 80, "#1B2552"), (220, 380, 95, "#2B3A78"),
                 (310, 300, 95, "#222F66")]
    for x, top, bw, col in buildings:
        d.rectangle([x, top, x + bw, h], fill=col)
        for wy in range(top + 18, h - 30, 34):
            for wx in range(x + 12, x + bw - 16, 22):
                if (wx * 7 + wy * 3) % 5 < 3:
                    d.rectangle([wx, wy, wx + 9, wy + 14], fill="#FFD66B")
    d.rectangle([0, h - 70, cw, h], fill="#070B1F")
    im = Image.new("RGB", (w, h), (0, 0, 0))
    im.paste(c, ((w - cw) // 2, 0))
    return im


def make_video(name, img):
    png, mp4 = WORK / f"{name}.png", WORK / f"{name}.mp4"
    img.save(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                    "-t", "30", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-colorspace", "bt709",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", str(mp4)], check=True)


def main():
    videos = {"sunset": landscape(), "desert": desert(), "city": city()}
    for name, img in videos.items():
        make_video(name, img)
    (WORK / "video.html").write_bytes((paths.WWW / "video.html").read_bytes())
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Quiet, directory=str(WORK)))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    t = pip.T()
    t.close_all()
    print("module:", t.install())
    # uncropped window (device px) and crop; the window then shrinks to the kept part
    plan = [("desert", {"x": 60, "y": 620, "w": 720, "h": 405}, {"t": 92 / 720, "b": 92 / 720}),
            ("sunset", {"x": 900, "y": 620, "w": 640, "h": 360}, {"l": 0.125, "r": 0.125}),
            ("city", {"x": 1600, "y": 560, "w": 960, "h": 540}, {"l": 0.3418, "r": 0.3418})]
    pids = []
    for i, (name, rect, crop) in enumerate(plan):
        if i:
            h = t.m.send("WebDriver:NewWindow", {"type": "tab", "focus": True})["handle"]
            t.m.send("WebDriver:SwitchToWindow", {"handle": h, "focus": True})
        t.m.navigate(f"http://127.0.0.1:{PORT}/video.html?src={name}.mp4"); time.sleep(1.5)
        pid = t.open_pip(wait=1.0)
        t.player_call(pid, "setRect", rect)
        time.sleep(0.8)
        st = t.player_call(pid, "setCrop", crop)
        print(name, st["rect"], {k: round(v, 3) for k, v in st["crop"].items()})
        pids.append((pid, st["rect"]))
    time.sleep(2.0)
    t.wait_controls_hidden()

    shots = []
    for pid, r in pids:
        rect = (r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])
        h = t.hwnd_of(rect)
        for _ in range(20):
            if h and not pip.occluded({"hwnd": h, "rect": rect}):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("a PiP window is covered; not capturing")
        shots.append(W.grab(rect))
    t.close_all()
    t.close()
    server.shutdown()

    # compose: wide film top left, 4:3 picture below it, the vertical video on the right
    dpr = 1.25
    gap = round(36 * dpr)
    film, pic, vert = shots
    left_w = max(film.width, pic.width)
    content_w = left_w + gap + vert.width
    content_h = max(film.height + gap + pic.height, vert.height)
    margin = round(56 * dpr)
    cw, ch = content_w + 2 * margin, content_h + 2 * margin
    canvas = Image.new("RGB", (cw, ch), BG)
    top = margin + (content_h - (film.height + gap + pic.height)) // 2
    places = [(film, (margin, top)), (pic, (margin, top + film.height + gap)),
              (vert, (margin + left_w + gap, margin + (content_h - vert.height) // 2))]
    radius = round(8 * dpr)
    for img, (x, y) in places:
        shadow = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(shadow).rounded_rectangle([x, y + 8, x + img.width, y + img.height + 8], radius=radius, fill=150)
        canvas.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(14)))
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
        canvas.paste(img, (x, y), mask)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {cw}x{ch})")


if __name__ == "__main__":
    main()
