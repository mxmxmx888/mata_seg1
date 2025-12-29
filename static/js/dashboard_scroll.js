{
  const globalWindow = typeof window !== "undefined" ? window : null;

  const initDashboardScroll = (win) => {
    const w = win || globalWindow;
    if (!w || !w.document || !w.history || w.__dashboardScrollInitialized) return;
    w.__dashboardScrollInitialized = true;
    if ("scrollRestoration" in w.history) {
      w.history.scrollRestoration = "manual";
    }
    if (typeof w.scrollTo === "function") {
      w.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initDashboardScroll };
  }

  /* istanbul ignore next */
  if (globalWindow && globalWindow.document) {
    const runInit = () => initDashboardScroll(globalWindow);
    if (globalWindow.document.readyState === "loading") {
      globalWindow.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
}
