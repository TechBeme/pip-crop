# Changelog

All notable changes to PiP Crop. Versions follow [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-09-22

First public release.

- New add-on ID, `pip-crop@techbeme.github.io`. If you installed an earlier
  build (`pipcrop@local`), remove it first.
- Installed copies update themselves from GitHub releases.
- Icon.
- Declares that it collects no data (`data_collection_permissions`).
- When two copies are present (the extension and the Firefox AutoConfig
  files, or two builds), only the first one to start is active instead of both
  handling the same windows.

## [1.1.1] - 2026-09-22

- Fixed: a dark strip along the side of the PiP window while Shift was held
  over an edge.

## [1.1.0] - 2026-09-22

- Dragging an edge outward stops exactly at the edge of the video, so no
  black area can appear past the frame.
- Fixed: releasing the mouse while it was still moving could leave the window
  with the wrong shape, which made the video look stretched. A drag now ends
  when Windows' own sizing loop ends.

## [1.0.0] - 2026-09-22

- Shift + drag an edge or corner of the native Picture-in-Picture window crops
  that side: the window shrinks and the video keeps its scale on screen.
- A normal drag resizes proportionally and keeps the crop; Shift +
  double-click resets it.
- Every PiP window has its own crop.
- LibreWolf extension (WebExtension Experiment) and Firefox AutoConfig
  install.
