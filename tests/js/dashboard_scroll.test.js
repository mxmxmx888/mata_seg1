describe("dashboard_scroll", () => {
  function loadWith(windowOverrides = {}) {
    jest.resetModules();
    global.scrollTo = jest.fn();
    const history = { scrollRestoration: "auto" };
    const baseWin = { document, history, scrollTo: jest.fn(), ...windowOverrides };
    const { initDashboardScroll } = require("../../static/js/dashboard_scroll");
    return { initDashboardScroll, history, win: baseWin };
  }

  test("sets scrollRestoration and scrolls to top", () => {
    const { initDashboardScroll, history, win } = loadWith();
    initDashboardScroll(win);
    expect(history.scrollRestoration).toBe("manual");
    expect(win.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
  });

  test("no scrollTo still sets restoration without error", () => {
    const { initDashboardScroll, history } = loadWith({ scrollTo: undefined });
    expect(() => initDashboardScroll({ document, history })).not.toThrow();
    expect(history.scrollRestoration).toBe("manual");
  });

  test("exits when already initialized or missing history", () => {
    const { initDashboardScroll, win } = loadWith();
    win.__dashboardScrollInitialized = true;
    expect(() => initDashboardScroll(win)).not.toThrow();

    const noHistoryWin = { document };
    expect(() => initDashboardScroll(noHistoryWin)).not.toThrow();
  });

  test("handles missing scrollRestoration and window gracefully", () => {
    const { initDashboardScroll } = loadWith({ history: {}, scrollTo: jest.fn() });
    initDashboardScroll({ document, history: {}, scrollTo: jest.fn() });
    expect(() => initDashboardScroll()).not.toThrow();
  });

  test("falls back to global window when no arg provided", () => {
    const { initDashboardScroll } = loadWith();
    delete window.__dashboardScrollInitialized;
    initDashboardScroll();
    expect(window.__dashboardScrollInitialized).toBe(true);
  });

  test("handles history without scrollRestoration property", () => {
    const history = {};
    const { initDashboardScroll } = loadWith({ history, scrollTo: jest.fn() });
    initDashboardScroll({ document, history, scrollTo: jest.fn() });
    expect(history.scrollRestoration).toBeUndefined();
  });
});
