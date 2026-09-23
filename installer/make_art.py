"""Renders the installer artwork from assets/logo.svg: the setup icon and the
wizard images, at every size Inno Setup picks from for the display scale.

Needs the test browser from tests/README.md (the logo is rasterized by the
browser, with transparency):

    python installer/make_art.py
"""
import base64, io, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "harness"))
from PIL import Image
import piptest as pip

HERE = Path(__file__).resolve().parent
ART = HERE / "art"
LOGO = (HERE.parent / "assets" / "logo.svg").read_bytes()
ICON_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SMALL_SIZES = [58, 77, 97, 124, 159]          # WizardSmallImageFile, 100% to 250%
SIDE_SIZES = [(202, 386), (269, 515), (336, 643), (430, 824), (538, 1030)]  # WizardImageFile

RENDER = """
const [svg, w, h, kind] = arguments;
const img = new Image();
img.src = 'data:image/svg+xml;base64,' + svg;
await img.decode();
const c = document.createElement('canvas');
c.width = w; c.height = h;
const g = c.getContext('2d');
if (kind === 'side') {
  const bg = g.createLinearGradient(0, 0, 0, h);
  bg.addColorStop(0, '#1E1B4B');
  bg.addColorStop(1, '#0F172A');
  g.fillStyle = bg;
  g.fillRect(0, 0, w, h);
  const s = w / 164;
  const logo = 92 * s;
  g.drawImage(img, (w - logo) / 2, 92 * s, logo, logo);
  g.fillStyle = '#F8FAFC';
  g.font = `600 ${Math.round(19 * s)}px "Segoe UI Semibold", "Segoe UI", Arial, sans-serif`;
  g.textAlign = 'center';
  g.fillText('PiP Crop', w / 2, 222 * s);
} else {
  g.drawImage(img, 0, 0, w, h);
}
return c.toDataURL('image/png');
"""


def render(t, w, h, kind="logo"):
    url = t.content("return (async () => {" + RENDER + "})();", base64.b64encode(LOGO).decode(), w, h, kind)
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGBA")


def main():
    ART.mkdir(exist_ok=True)
    t = pip.T()
    # LibreWolf's fingerprinting protection returns noise from canvas reads
    t.chrome("""for (const p of ["privacy.resistFingerprinting", "privacy.fingerprintingProtection"])
      Services.prefs.setBoolPref(p, false); return 1;""")
    t.m.navigate("about:blank")
    icons = [render(t, s, s) for s in ICON_SIZES]
    icons[-1].save(ART / "pip-crop.ico", format="ICO", sizes=[(s, s) for s in ICON_SIZES], append_images=icons[:-1])
    for s in SMALL_SIZES:
        render(t, s, s).save(ART / f"small-{s}.png", optimize=True)
    for w, h in SIDE_SIZES:
        render(t, w, h, "side").convert("RGB").save(ART / f"wizard-{w}.png", optimize=True)
    t.close()
    for f in sorted(ART.iterdir()):
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
