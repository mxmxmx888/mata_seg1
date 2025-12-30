(() => {
const globalContext = typeof globalThis !== "undefined" ? globalThis : /* istanbul ignore next */ {};
const hasModuleExports =
  !globalContext.__PROFILE_SCRIPTS_BROWSER__ &&
  typeof module !== "undefined" &&
  module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const modalsModule = hasModuleExports
  ? require("./profile_modals")
  : globalWindow && globalWindow.ProfileModals;
const infiniteModule = hasModuleExports
  ? require("./profile_infinite")
  : globalWindow && globalWindow.ProfileInfinite;

function resolveWindow(win) {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
}

function markInitialized(w, flag) {
  if (w[flag]) return false;
  w[flag] = true;
  return true;
}

function initProfileScripts(win) {
  const w = resolveWindow(win);
  if (!w || !markInitialized(w, "__profileScriptsInitialized")) return;
  const doc = w.document;
  const modalDeps =
    modalsModule && typeof modalsModule.initProfileModals === "function"
      ? modalsModule.initProfileModals(w, doc)
      : null;
  if (infiniteModule && typeof infiniteModule.initProfileInfinite === "function") {
    infiniteModule.initProfileInfinite(w, doc, modalDeps || {});
  }
}

function autoInitProfileScripts() {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initProfileScripts(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
}

if (hasModuleExports) {
  module.exports = { initProfileScripts };
}

/* istanbul ignore next */
autoInitProfileScripts();
})();
