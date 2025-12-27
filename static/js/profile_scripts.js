(function (global) {
  const modalsModule =
    typeof module !== "undefined" && module.exports
      ? require("./profile_modals")
      : global && global.ProfileModals;
  const infiniteModule =
    typeof module !== "undefined" && module.exports
      ? require("./profile_infinite")
      : global && global.ProfileInfinite;

  function resolveWindow(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    return w && w.document ? w : null;
  }

  function markInitialized(w, flag) {
    if (w[flag]) return false;
    w[flag] = true;
    return true;
  }

  function initProfileScripts(win) {
    const w = resolveWindow(win);
    if (!w) return;
    if (!markInitialized(w, "__profileScriptsInitialized")) return;
    const doc = w.document;
    const modalDeps =
      modalsModule && typeof modalsModule.initProfileModals === "function"
        ? modalsModule.initProfileModals(w, doc)
        : null;
    if (infiniteModule && typeof infiniteModule.initProfileInfinite === "function") {
      infiniteModule.initProfileInfinite(w, doc, modalDeps || {});
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initProfileScripts };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initProfileScripts(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
