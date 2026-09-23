# Tests

End-to-end tests against a real LibreWolf or Firefox on **Windows**. The
harness starts the browser with an isolated profile, controls it through
Marionette with chrome-context access (privileged JavaScript in the parent
process, including inside PiP windows), and checks results against
screenshots of the PiP window.

## Setup

- Windows 10 or 11, with LibreWolf and/or Firefox
- Python 3 with `numpy`, `pillow` and `psutil`
- `ffmpeg` on the PATH, to generate the test videos
- optional: [Shaka Packager](https://github.com/shaka-project/shaka-packager)
  (`packager` on the PATH, or `SHAKA_PACKAGER`), for the DRM test video

```sh
pip install numpy pillow psutil
python tests/www/gen_videos.py                   # test videos, in tests/www/
python tests/harness/serve.py                    # keep it running
python tests/harness/ctl.py launch librewolf 2829   # test browser
python tests/e2e/t_sim.py                        # run a test
```

`serve.py` serves `tests/www/` on port 8765 (same origin), 8766 (another
origin, without CORS headers) and 8767 (another origin, with CORS). The test
browser's profile and everything the tests write (screenshots, calibration,
results) go to `tests/out/`, which git ignores.

| Variable | |
|---|---|
| `PIPCROP_PORT` | Marionette port of the test browser (default 2829) |
| `PIPCROP_NO_INJECT=1` | test the copy the browser already runs (installed extension or AutoConfig) instead of injecting `src/pipcrop.js` |
| `PIPCROP_LIBREWOLF`, `PIPCROP_FIREFOX` | path to the browser's `.exe` |
| `PIPCROP_TEST_OUT` | output folder instead of `tests/out/` |

## How results are checked

The test videos encode their own coordinates in every pixel (red = x,
green = y) and have a grid line every 10 %. `harness/analyze.py` finds the
grid lines in a screenshot of the PiP window and compares them with where the
crop says they should be. That measures the visible part of the source, the
scale on each axis (stretch) and black bands, without depending on colors.

The harness only captures a PiP window that is exactly where the test put it
and not covered by another window, so it never keeps pixels of anything else
on your screen.

## Simulated and real input

Most tests simulate input: the module's reader of the physical keyboard and
mouse is replaced by a fake (`PipCrop._setNativeForTests`), and the window
steps that Windows' sizing loop would produce are applied with
`SetWindowPos`. They don't touch your mouse or keyboard, but they do open
windows on screen.

`t_real.py`, `t_real2.py`, `t_gesture.py` and `t_corner.py` use the real mouse
and keyboard (`SendInput`). They wait until the mouse and keyboard have been
idle for a few seconds (20 s before `t_real.py` starts), and redo a gesture
if you touch them during it.

## e2e/

| Test | Checks |
|---|---|
| `t_sim.py` | gesture battery: crop each side, uncrop, overshoot, minimum size, on 16:9, 4:3 or vertical video |
| `t_clamp.py` | dragging outward stops at the edge of the video; releasing while the mouse still moves leaves no stretch |
| `t_armed.py` | no dark strip while Shift is held on an edge or during a drag |
| `t_calib.py` | the size limit given to Windows equals the distance to the edge of the video |
| `t_late.py` | Shift pressed after the drag has started |
| `t_multi.py` | three PiP windows at once, with independent crops |
| `t_misc.py` | fullscreen, a resolution change while cropped, fast and jittery drags, the hint |
| `t_hint.py` | the outline follows Shift |
| `t_api.py` | crops set through the API |
| `t_xorigin.py` | cross-origin video without CORS |
| `t_eme.py` | DRM (ClearKey) video |
| `t_real.py`, `t_real2.py`, `t_gesture.py`, `t_corner.py` | gestures with the real mouse and keyboard |
| `t_ext.py` | installs the built `.xpi` without a restart, then restarts the browser |
| `t_double.py` | a second copy of the module stays inactive |
| `t_update.py` | the extension updates itself from a local server |
| `t_installer.py` | the Windows installer: installs into test LibreWolf profiles and a portable Firefox, checks both, uninstalls and checks everything was put back |
| `perf.py` | CPU and GPU use: native PiP, PiP Crop, canvas route |

`t_ext.py` and `t_update.py` use the build in `dist/`, so run
`python tools/build.py` first; `t_update.py` needs `--repo`, for
`dist/updates.json`.

`t_installer.py` needs a test build of the installer, which runs without
elevation: `ISCC /DAppVersion=X.Y.Z /DTestBuild installer\pip-crop.iss`, then
`python tests/e2e/t_installer.py dist\pip-crop-X.Y.Z-setup.exe`.

`demo_gif.py` and `screenshots.py` record the README images in
`docs/images/` (simulated input on real PiP windows).

## research/ and harness/

`research/` has the scripts behind [docs/research.md](../docs/research.md):
the canvas + `captureStream` route and other approaches that were dropped.
They are experiments, not regression tests.

`harness/` is the shared code:

| | |
|---|---|
| `mn.py` | Marionette client and browser launcher |
| `ctl.py` | command line: launch the test browser, run JavaScript in it, quit |
| `piptest.py` | test helpers: open PiP windows, call the module, take screenshots |
| `sim.py` | simulated input and sizing-loop steps |
| `analyze.py` | screenshot analysis |
| `winutil.py` | Win32 helpers: windows, screen capture, `SendInput`, idle time |
| `serve.py` | local HTTP server with Range support |
| `paths.py` | where files are read and written |
