PiP Crop for Firefox (AutoConfig)
=================================

Firefox release only runs signed extensions, and extensions cannot reach the
Picture-in-Picture window, so PiP Crop is loaded by Firefox's own AutoConfig
mechanism instead (three files in the Firefox installation folder).

Install: open PowerShell as Administrator in this folder and run

    powershell -ExecutionPolicy Bypass -File install.ps1

then restart Firefox. Firefox updates keep the files.

Uninstall:

    powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall

Firefox in another folder: add -FirefoxDir "D:\path\to\Firefox" (the folder
that contains firefox.exe).

Manual install: copy these into the folder that contains firefox.exe,
keeping the layout:

    defaults\pref\autoconfig.js
    pipcrop.cfg
    pipcrop.js

Use: Shift + drag an edge of the PiP window to crop that side, drag outward
to uncrop, Shift + double-click to reset.
