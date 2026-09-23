# Research notes

What was tried before settling on cropping inside the PiP player window, and
why the alternatives were dropped. Everything here was measured on LibreWolf
156.0 and Firefox 156.0.1 on Windows 11, with the harness in
[`tests/`](../tests); the experiment scripts are in
[`tests/research/`](../tests/research).

The goal was to crop the native video PiP window interactively, with these
requirements:

- the window really shrinks;
- the part that is kept stays at the same scale, with no black bars, no
  stretching and no zoom;
- several PiP windows work at once;
- no external program and no screen-capture window.

## How results were measured

The test videos encode their own coordinates in every pixel (red = x,
green = y) and have a grid line every 10 %
([`tests/www/gen_videos.py`](../tests/www/gen_videos.py)). The harness takes a
screenshot of the PiP window, finds the grid lines and compares them with the
positions predicted from the crop. That measures which part of the source is
visible, at what scale on each axis (stretch), and whether there are black
bars. It does not rely on colors, which display color management changes.

## Approach 1: change the video the page gives to PiP

The idea: from a content script, draw the cropped region of the video into a
canvas, turn it into a stream with `canvas.captureStream()`, play that in a
hidden `<video>` and put that one in PiP
([`tests/www/canvas_crop.html`](../tests/www/canvas_crop.html)).

| Experiment | Result |
|---|---|
| Resize the canvas in place (same track) | `videoWidth` and `resize` update, and Firefox refits the PiP window. But the refit keeps the window **height**, so a vertical crop enlarges the picture instead of shrinking the window: cropping 10 % top and bottom is a 25 % zoom. |
| Replace the track in the same `MediaStream` | The `<video>` freezes: `videoWidth` keeps the old size and no `resize` fires. |
| Assign a new `srcObject` | Firefox closes the PiP window. |
| Cross-origin video without CORS headers | The canvas is tainted and `captureStream()` throws `SecurityError`: the PiP is black. |
| DRM (EME) video | `drawImage` gives black pixels. |
| LibreWolf's fingerprinting protection | Reading a canvas needs a per-site permission. |
| CPU | About 97 % of one core for 1080p30, against about 11 % for the native PiP (below). |
| `VideoFrame`, `MediaStreamTrackGenerator`, `VideoTrackGenerator` | Not available in LibreWolf 156 with its default settings, so there is no cheaper WebCodecs path. |
| `video.requestPictureInPicture()` | Only one API PiP window can exist at a time (`closeApiPipWindowIfOpen`), which rules out several PiPs. The native PiP toggle has no such limit. |

So the canvas route only works for same-origin or CORS-enabled video without
DRM, zooms on vertical crops and costs a CPU core. It was dropped.

## Approach 2: crop inside the PiP player window

This is what PiP Crop does; [architecture.md](architecture.md) has the
details. Reading Firefox's window code (`widget/windows/nsWindow.cpp`) turned
up several obstacles, each with a workaround:

| Obstacle | Workaround |
|---|---|
| The resize border is non-client area, hit-tested by nsWindow: content can't take it over and gets no events while it is dragged. | Read Shift, the mouse button and the cursor through js-ctypes, and ask the window's own `WM_NCHITTEST` which edge is under the cursor. |
| The aspect-ratio lock is applied in Windows' sizing loop (`WM_SIZING`) and by an `EnforceAspectRatio` runnable. | Release the lock before the drag starts (while Shift is over an edge) and set it again after. |
| The 4-argument `nsWindow::Resize` (move and resize) doesn't refresh the aspect lock; the size-only one does. | Set the lock again after every move-and-resize. |
| Windows reads the window's size limits (`WM_GETMINMAXINFO`) once, when the sizing loop starts. They come from the widget's size constraints, which come from the root element's `max-width`/`max-height` on the next paint. | Set those limits while Shift is over an edge, before the click, so Windows itself stops the edge at the edge of the video. |
| Firefox adds a normal window frame to those limits (`NormalSizeModeClientToWindowSizeDifference`), which the PiP window doesn't have: 18 × 9 px at 125 %. | Measure the difference per window and per display scale, and subtract it. Size the video container with the viewport so the smaller root element never leaves a strip uncovered. |
| The sizing loop keeps applying queued mouse moves after the button is released. | End the gesture when `GetGUIThreadInfo` stops reporting `GUI_INMOVESIZE`, not when the button comes up. |
| Ctrl + drag is taken by the PiP window's corner snapping (`Player.onMouseUp`). | Use Shift (or Alt). |

### Cost

`tests/e2e/perf.py`: a 1080p30 H.264 video, averaged over 15 s.

| | CPU (% of one core) | GPU 3D | GPU video decode |
|---|---|---|---|
| Native PiP, no crop | 11.7 % | 1.0 % | 9.7 % |
| Native PiP + PiP Crop | 10.7 % | 2.4 % | 13.5 % |
| Canvas + `captureStream` | 97.1 % | 8.5 % | 7.3 % |

Raw data: [evidence/perf.json](evidence/perf.json).

## Evidence

Screenshots of the PiP window taken by the harness (the labels in the images
are in Portuguese):

- [evidence/01_crop_vs_canvas.png](evidence/01_crop_vs_canvas.png): the
  native PiP without a crop, crops set through the API, crops made with real
  mouse and keyboard input on each side and a corner, and the canvas route
  for comparison: a horizontal crop works, a vertical crop zooms, and
  cross-origin video without CORS is black.
- [evidence/02_real_input_and_multi_pip.png](evidence/02_real_input_and_multi_pip.png):
  a real-input session. It starts from 600×338; Shift + left edge +60 px and
  Shift + right edge −60 px give 480×338 showing the middle 1536×1080 of the
  source. Then the top and bottom are cropped and part of the left is
  uncropped, a move without Shift keeps the crop, and Shift + double-click
  resets it. The last three images are three PiP windows at once (16:9, 4:3
  and vertical video), each with its own crop.
- [evidence/05_fullscreen_crop.png](evidence/05_fullscreen_crop.png):
  fullscreen with a crop, letterboxed.
- [evidence/real_input_run.json](evidence/real_input_run.json): the log of the
  real-input run, with the window rectangle, crop, visible source region,
  grid match, scale, stretch and black pixels at each step.
