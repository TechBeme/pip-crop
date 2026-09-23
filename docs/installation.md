# Installation

PiP Crop changes the browser's own Picture-in-Picture window, which the
normal WebExtension APIs cannot reach. It therefore runs as privileged code,
and how it is loaded depends on the browser:

| Browser | Package | Updates |
|---|---|---|
| LibreWolf (Windows) | installer, or `pip-crop-<version>.xpi` | automatic, from GitHub releases |
| Firefox release (Windows) | installer, or `pip-crop-<version>-firefox-autoconfig.zip` | run the installer of the new version |
| Firefox Developer Edition, Nightly | `pip-crop-<version>.xpi` (untested) | automatic |

Requirements: Windows 10 or 11 and a browser based on Firefox 140 or newer.
PiP Crop is tested on Windows 11 with LibreWolf 156.0 and Firefox 156.0.1, on
displays at 100 % and 125 %.

Download the files from the [latest release](https://github.com/TechBeme/pip-crop/releases/latest).

## Installer (recommended)

Run `pip-crop-<version>-setup.exe`, click **Next**, check the browsers and
click **Install**. Windows asks for permission (Firefox's folder is
protected). When it finishes, close the browser completely and open it again.

Windows may show "Windows protected your PC", because the installer is not
signed with a paid certificate: click **More info**, then **Run anyway**. The
installer is built by GitHub Actions from this repository, and the release's
`SHA256SUMS.txt` has its checksum.

What it changes, and what Settings → Apps → PiP Crop → Uninstall puts back:

| Browser | Change |
|---|---|
| LibreWolf, every profile listed in `%APPDATA%\librewolf\profiles.ini` | copies the extension to `extensions\pip-crop@techbeme.github.io.xpi` and adds four prefs to `user.js`, between `// >>> PiP Crop` and `// <<< PiP Crop` |
| Firefox, each installation it finds | copies the three AutoConfig files described [below](#firefox-release-without-the-installer) |

The four LibreWolf prefs let LibreWolf load an unsigned extension with an
experimental API (`xpinstall.signatures.required = false`,
`extensions.experiments.enabled = true`) and pick up the extension file from
the profile without asking (`extensions.startupScanScopes = 1`,
`extensions.autoDisableScopes = 14`). The installer remembers any values you
had set for them before and restores those values on uninstall.

The installer does not need the browser to be closed. It cannot help when:

- LibreWolf was never opened, so it has no profile yet: open it once, then
  run the installer again;
- Firefox already uses AutoConfig for something else, such as a
  userChrome.js loader (see [below](#if-you-already-use-autoconfig));
- the browser is the Microsoft Store version of Firefox or a portable
  LibreWolf: use the manual steps.

## LibreWolf, without the installer

1. Open `about:config` and set:
   - `xpinstall.signatures.required` to `false`
   - `extensions.experiments.enabled` to `true`
2. Open `about:addons`, click the gear icon, choose **Install Add-on From
   File…** and pick `pip-crop-<version>.xpi`. No restart is needed.

LibreWolf shows "could not be verified for use in LibreWolf" under the
add-on. It shows that for every unsigned extension; PiP Crop cannot be signed
by Mozilla (see [the README](../README.md#why-isnt-pip-crop-on-addonsmozillaorg)).

**Updates** are automatic: the add-on's update URL points at the
`updates.json` of this repository's latest release, and LibreWolf checks it
like any other add-on update (the download is verified with a SHA-256 hash).

**Uninstall** from `about:addons`.

## Firefox (release), without the installer

Firefox release only runs extensions signed by Mozilla, so PiP Crop is loaded
by Firefox's [AutoConfig](https://support.mozilla.org/kb/customizing-firefox-using-autoconfig):
three files in the Firefox installation folder.

1. Extract `pip-crop-<version>-firefox-autoconfig.zip`.
2. Open PowerShell **as Administrator** in the extracted folder and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
3. Close every Firefox window and start Firefox again.

| Option | |
|---|---|
| `-FirefoxDir "D:\path\to\Firefox"` | Firefox installed somewhere other than `C:\Program Files\Mozilla Firefox` (the folder with `firefox.exe`) |
| `-Uninstall` | remove the three files |
| `-SkipAdminCheck` | a portable Firefox in a folder you can write to |

Firefox updates keep the files. To update PiP Crop, run `install.ps1` from
the zip of the new version.

The installer copies:

| File | Purpose |
|---|---|
| `defaults\pref\autoconfig.js` | turns AutoConfig on and points it at `pipcrop.cfg` |
| `pipcrop.cfg` | loads `pipcrop.js` once the first browser window has started |
| `pipcrop.js` | the module |

### If you already use AutoConfig

If `defaults\pref\autoconfig.js` already points at another `.cfg` (for
example a userChrome.js loader), the installer stops without changing
anything. Copy `pipcrop.js` somewhere and load it from your own `.cfg`:

```js
const scope = { Services, ChromeUtils, Cc: Components.classes, Ci: Components.interfaces, Cu: Components.utils };
Services.scriptloader.loadSubScriptWithOptions("file:///C:/path/to/pipcrop.js",
  { target: scope, allowUnsafeURL: true });
scope.PipCrop.install();
```

Firefox 15x only loads `file:` scripts this way with `allowUnsafeURL: true`.
Run it after the first browser window has started (for example on
`browser-delayed-startup-finished`, as `pipcrop.cfg` does).

## Firefox Developer Edition and Nightly

These builds let you turn both prefs of the LibreWolf steps on, so the `.xpi`
should work there the same way. This has not been tested.

## Settings

Optional, in `about:config`:

| Pref | Default | |
|---|---|---|
| `extensions.pipcrop.modifier` | `shift` | `alt` to use Alt instead of Shift. Ctrl is not possible: Ctrl + drag is the PiP window's own corner snapping. |
| `extensions.pipcrop.hint` | `true` | Show an outline while the modifier is held over the window |
| `extensions.pipcrop.debug` | `false` | Keep a per-window event log |

## Troubleshooting

**Shift + drag resizes normally instead of cropping.** Check in the Browser
Console (`Ctrl + Shift + J`) that PiP Crop is active:

```js
ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs")
  .PictureInPicture.__pipcrop?.version
```

It prints the version, or `undefined` when PiP Crop is not loaded. In
LibreWolf, check that both prefs are set and that the add-on is enabled. In
Firefox, check that the three files are in the Firefox folder and that you
restarted Firefox completely.

**"PiP Crop … is already active, not installing twice"** in the Browser
Console means two copies are present, for example the extension and the
AutoConfig files. The first one to start is used; remove the other.

**A crop drag doesn't stop at the edge of the video** when you press Shift
and click at almost the same moment. Hold Shift over the edge for a moment
before clicking (see the limitations below).

## Known limitations

- The crop is not saved. Every new PiP window opens uncropped.
- The limit at the edge of the video is set up while Shift is held with the
  cursor on an edge, checked every 50 ms. If Shift and the click come within
  about 50 ms of each other, the right and bottom edges still stop at the
  video, but the left and top edges can pass it during the drag and snap back
  when you let go.
- PiP subtitles (WebVTT) are drawn over the whole frame, so cropping the
  bottom can hide them.
- Linux and macOS use a fallback without native input that has not been
  tested.
- The crop works on DRM (EME) video, but that could only be checked from the
  window geometry: the browser blocks screen capture of protected video.
