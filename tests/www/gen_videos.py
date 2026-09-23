# Generates measurable test videos.
# Every pixel encodes its own source coordinate: R = x/W*255, G = y/H*255, B = 128.
# So nothing in the frame is pure black (letterbox bars are detectable), and a
# screenshot of the PiP tells which source region is visible and at what scale.
import os, shutil, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))

def base_image(W, H, path):
    x = np.linspace(0, 255, W, dtype=np.float32)
    y = np.linspace(0, 255, H, dtype=np.float32)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:, :, 0] = x[None, :].round().astype(np.uint8)
    img[:, :, 1] = y[:, None].round().astype(np.uint8)
    img[:, :, 2] = 128
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arialbd.ttf", max(18, H // 40))
    except OSError:
        font = ImageFont.load_default()
    # thin grid every 10%, labels near edges
    for i in range(1, 10):
        gx = round(W * i / 10)
        gy = round(H * i / 10)
        d.line([(gx, 0), (gx, H)], fill=(255, 255, 255), width=2)
        d.line([(0, gy), (W, gy)], fill=(255, 255, 255), width=2)
        d.text((gx + 4, H * 0.45), f"x{i*10}", fill=(255, 255, 255), font=font)
        d.text((W * 0.46, gy + 4), f"y{i*10}", fill=(255, 255, 255), font=font)
    # circle for visual stretch check
    r = min(W, H) * 0.18
    cx, cy = W / 2, H / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=6)
    d.text((12, 12), f"{W}x{H}", fill=(255, 255, 255), font=font)
    im.save(path)

def make(W, H, name, seconds=120):
    png = os.path.join(OUT, f"{name}.png")
    base_image(W, H, png)
    fs = max(24, H // 18)
    vf = (
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='%{{pts\\:hms}}':"
        f"x=(w-tw)/2:y=h*0.62:fontsize={fs}:fontcolor=white:box=1:boxcolor=0x404040@1,"
        f"drawbox=x='mod(t*{W//8},{W})':y={int(H*0.75)}:w={max(8,W//60)}:h={max(8,H//30)}:color=white:t=fill,"
        f"scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
    )
    mp4 = os.path.join(OUT, f"{name}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", png,
           "-vf", vf, "-t", str(seconds), "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "16", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    print("ok", mp4)

def make_cenc(src="v169", name="v169_cenc", seconds=90):
    """ClearKey-encrypted copy of a test video for eme.html. Needs Shaka Packager
    (https://github.com/shaka-project/shaka-packager) as `packager` on PATH or in
    $SHAKA_PACKAGER; only the EME tests use this file."""
    packager = os.environ.get("SHAKA_PACKAGER") or shutil.which("packager")
    if not packager:
        print("skipped", name, "(Shaka Packager not found)")
        return
    clip = os.path.join(OUT, f"{src}_{seconds}s.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, f"{src}.mp4"),
                    "-t", str(seconds), "-c:v", "copy", "-an", clip], check=True)
    # key id and key must match eme.html
    keys = "label=:key_id=0123456789abcdef0123456789abcdef:key=00112233445566778899aabbccddeeff"
    subprocess.run([packager, f"in={clip},stream=video,output={os.path.join(OUT, name + '.mp4')}",
                    "--enable_raw_key_encryption", "--keys", keys, "--protection_systems", "CommonSystem",
                    "--clear_lead", "0", "--protection_scheme", "cenc"], check=True)
    print("ok", os.path.join(OUT, name + ".mp4"))

if __name__ == "__main__":
    make(1920, 1080, "v169")      # 16:9
    make(1440, 1080, "v43")       # 4:3
    make(1080, 1920, "vvert")     # vertical 9:16
    make(1280, 720, "v169_720")   # same 16:9 at lower resolution (resolution-change tests)
    make_cenc()                   # EME (ClearKey) copy of v169, if Shaka Packager is available
