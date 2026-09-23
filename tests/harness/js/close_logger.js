const { PictureInPicture: P } = ChromeUtils.importESModule("moz-src:///toolkit/components/pictureinpicture/PictureInPicture.sys.mjs");
if (!P.__closeLog) {
  P.__closeLog = [];
  const origSingle = P.closeSinglePipWindow, origClose = P.closePipWindow;
  P.closeSinglePipWindow = function (data) {
    P.__closeLog.push({ t: Date.now(), via: "closeSinglePipWindow", reason: data && data.reason });
    return origSingle.call(this, data);
  };
  P.closePipWindow = function (win) {
    P.__closeLog.push({ t: Date.now(), via: "closePipWindow", stack: new Error().stack.split("\n").slice(1, 7).join(" | ") });
    return origClose.call(this, win);
  };
  Services.ww.registerNotification({ observe(subject, topic) {
    try {
      if (topic === "domwindowclosed" && subject.document?.documentElement?.getAttribute("windowtype") === "Toolkit:PictureInPicture") {
        P.__closeLog.push({ t: Date.now(), via: "domwindowclosed" });
      }
    } catch (e) {}
  } });
}
return "close logger installed, entries: " + P.__closeLog.length;
