// Opens native PiP for the playing video of the selected tab (same path as Ctrl+Shift+]).
const bw = Services.wm.getMostRecentWindow("navigator:browser");
const before = new Set([...Services.wm.getEnumerator("Toolkit:PictureInPicture")]);
const actor = bw.gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.getActor("PictureInPictureLauncher");
actor.sendAsyncMessage("PictureInPicture:KeyToggle");
let win = null;
for (let i = 0; i < 100 && !win; i++) {
  await new Promise(r => setTimeout(r, 100));
  win = [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].find(w => !before.has(w)) || null;
}
if (!win) return "no pip window";
await new Promise(r => setTimeout(r, 1500));
return { count: [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].length,
  screenX: win.screenX, screenY: win.screenY, outer: [win.outerWidth, win.outerHeight],
  inner: [win.innerWidth, win.innerHeight], dpr: win.devicePixelRatio };
