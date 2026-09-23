return [...Services.wm.getEnumerator("Toolkit:PictureInPicture")].map(w => ({
  screenX: w.screenX, screenY: w.screenY, outer: [w.outerWidth, w.outerHeight], inner: [w.innerWidth, w.innerHeight] }));
