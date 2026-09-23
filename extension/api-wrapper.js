/* PiP Crop — WebExtension Experiment entry point (parent process).
 * tools/build.py replaces the marker below with src/pipcrop.js, so the whole
 * module ships inside api.js and lives in this closure only. */

/* global ExtensionAPI */
"use strict";

this.pipcrop = (() => {
  /* @@PIPCROP_MODULE@@ */

  return class extends ExtensionAPI {
    onStartup() {
      PipCrop.install();
    }

    onShutdown(isAppShutdown) {
      if (!isAppShutdown) {
        PipCrop.uninstall();
      }
    }

    getAPI() {
      return { pipcrop: {} };
    }
  };
})();
