(function (global) {
  function initDashboardScroll(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document || !w.history) return;
    if (w.__dashboardScrollInitialized) return;
    w.__dashboardScrollInitialized = true;

    if ("scrollRestoration" in w.history) {
      w.history.scrollRestoration = "manual";
    }
    if (typeof w.scrollTo === "function") {
      w.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initDashboardScroll };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initDashboardScroll(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
