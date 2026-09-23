# Architecture

Everything happens in the browser's parent process, inside the PiP player
window. Nothing runs in the page.

## The PiP window

Firefox's video Picture-in-Picture (`toolkit/components/pictureinpicture/`)
opens `chrome://global/content/pictureinpicture/player.xhtml` as a chrome
window without a title bar (`"chrome,alwaysontop,lockaspectratio,resizable,dialog,titlebar=no"`),
with a 16 px resize margin (`windowUtils.setResizeMargin`). The video in it is
a remote `<xul:browser>` showing a visual clone of the page's `<video>`
(`cloneElementVisually`), sized 100vw × 100vh. When the source video changes
size, the page's actor sends `PictureInPicture:Resize`, and
`PictureInPicture.resizePictureInPictureWindow` refits the window, keeping
its height.

PiP Crop wraps two functions of the `PictureInPicture` module:

- `openPipWindow`, to attach a controller to every new player window. Each
  window has its own crop state.
- `resizePictureInPictureWindow`, to pass it the *cropped* video size, so
  Firefox's own refit keeps the crop's aspect ratio when the resolution
  changes (adaptive streaming, a new source).

## Showing a crop

The crop is stored as fractions of the source frame per side (`l`, `r`, `t`,
`b`). Normally the `<browser>` is laid out in percentages:

```
width  = 100 / (1 − l − r) %      left = −100 · l / (1 − l − r) %
height = 100 / (1 − t − b) %      top  = −100 · t / (1 − t − b) %
```

The window becomes an opening onto a frame larger than itself, and the
compositor clips what falls outside. Nothing is copied and no script runs per
frame. The window's aspect-ratio lock (`nsIAppWindow.lockAspectRatio`) is set
to the cropped shape, so a normal drag resizes proportionally and the
percentages stay exact at any size. Plain resizing runs no script at all.

In fullscreen, the cropped region is centered with a `clip-path` and
letterboxed.

## The crop gesture

The resize border of the PiP window is non-client area: Windows handles it,
through nsWindow's `WM_NCHITTEST` (answered from geometry alone). Content
cannot take it over, and no DOM events arrive while the border is dragged.
So PiP Crop reads the input state itself, through js-ctypes:

1. **Arming.** Every 50 ms, and on key and mouse events in the window, it
   reads Shift (`GetAsyncKeyState`) and the cursor (`GetCursorPos`), and asks
   the window which edge is under the cursor by sending `WM_NCHITTEST` to its
   own HWND. With Shift over an edge, before any click, it:
   - releases the aspect lock, so one edge can move alone;
   - anchors the `<browser>` in pixels to the edges that won't move, so the
     video stays still on screen while the window edge slides over it;
   - sets `max-width`/`max-height` on the player's root element to the
     distance from the fixed edge to the edge of the video. Firefox hands
     those to the widget on the next paint (`PresShell::SyncWindowPropertiesIfNeeded`)
     and answers `WM_GETMINMAXINFO` with them, so Windows' own sizing loop
     stops the edge at the video. They have to be in place before the button
     goes down: Windows reads the limits once, when its sizing loop starts.
2. **Frame compensation.** When Firefox turns those limits into window limits
   it adds the size of a normal window frame
   (`NormalSizeModeClientToWindowSizeDifference`), which the frameless PiP
   window doesn't have: 18 × 9 px at 125 %. PiP Crop measures this per window
   by setting a limit larger than the window and reading `WM_GETMINMAXINFO`
   back, and measures again after the window moves to a display with another
   scale. Because the compensated root element can be narrower than the
   window, the video's container is sized with the viewport (`100vw`) instead.
3. **End of the drag.** The drag ends when Windows' modal sizing loop ends
   (`GetGUIThreadInfo` → `GUI_INMOVESIZE`), not when the button comes up. The
   loop keeps applying queued mouse moves after the button is released, and
   finishing early would lock the window to a shape the video doesn't have,
   which looks stretched.
4. **Commit.** The crop is recomputed from the final window rectangle,
   clamped to the video frame and to a minimum size (4 % of the frame, at
   least 32 px), applied with one `setPositionAndSize` call, and the aspect
   lock is set to the new shape. That 4-argument resize doesn't refresh the
   lock in nsWindow, so it is set again explicitly.

If Shift comes after the drag has started, the sizing loop already has its
limits. The gesture still works: the lock is released on the next turn of
the event loop (nsWindow may have just queued an `EnforceAspectRatio`
runnable), the right and bottom edges are capped (Firefox clamps an oversized
window by keeping its top-left corner), and a left or top overshoot is undone
when the drag ends.

Ctrl is not an option for the modifier: Ctrl + drag is the PiP window's own
corner snapping (`Player.onMouseUp`). Alt works (`extensions.pipcrop.modifier`).

## Without js-ctypes

Linux and macOS have no js-ctypes input reader here. The module falls back to
the modifier state seen in the PiP window's own DOM events, and ends a
gesture on the next mouse event or after 400 ms without one. This path has
not been tested.

## Files

| File | |
|---|---|
| `src/pipcrop.js` | the module: `PipCrop.install()`, `PipCrop.uninstall()` |
| `extension/` | WebExtension Experiment wrapper. `api.js` is `api-wrapper.js` with the module inlined by `tools/build.py`; `onStartup` installs, `onShutdown` uninstalls |
| `firefox-autoconfig/` | `defaults/pref/autoconfig.js` turns AutoConfig on; `pipcrop.cfg` loads `pipcrop.js` from the Firefox folder when the first browser window has finished starting (`browser-delayed-startup-finished`) |

If two copies are present (the extension and the AutoConfig files, say), the
first one to start is used and the second logs an error instead of
installing.

## Diagnostics

In the Browser Console:

```js
const P = ChromeUtils.importESModule(
  "moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs").PictureInPicture.__pipcrop;
P.version;
const win = Services.wm.getMostRecentWindow("Toolkit:PictureInPicture");
P.player(win).status();          // crop, window rect, arming, measured frame compensation
P.player(win).setCrop({ l: 0.1, r: 0.1 });
```

With `extensions.pipcrop.debug` set to `true`, `P.player(win).debugLog`
records geometry changes, arming and gestures.
