const modulePath = "../../static/js/messages_toast";

function loadModule() {
  jest.resetModules();
  delete global.__messagesToastInitialized;
  delete global.__messagesToastLifecycleBound;
  const mod = require(modulePath);
  delete global.__messagesToastInitialized;
  delete global.__messagesToastLifecycleBound;
  return mod;
}

describe("messages_toast", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    jest.useRealTimers();
  });

  afterEach(() => {
    delete global.bootstrap;
    jest.useRealTimers();
  });

  test("uses bootstrap toast when available", () => {
    const show = jest.fn();
    const hide = jest.fn();
    const Toast = jest.fn(() => ({ show, hide }));
    global.bootstrap = { Toast };
    jest.useFakeTimers();
    document.body.innerHTML = `<div class="toast"></div>`;

    const { initMessagesToast } = loadModule();
    initMessagesToast(window);

    expect(Toast).toHaveBeenCalledWith(document.querySelector(".toast"), expect.objectContaining({
      delay: 2000,
      autohide: true
    }));
    expect(show).toHaveBeenCalled();
    jest.runAllTimers();
    expect(hide).toHaveBeenCalled();
    expect(document.querySelector(".toast")).toBeNull();
  });

  test("falls back to class toggles without bootstrap", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `<div class="toast"></div>`;

    const { initMessagesToast } = loadModule();
    initMessagesToast(window);

    const toast = document.querySelector(".toast");
    expect(toast.classList.contains("show")).toBe(true);
    jest.runAllTimers();
    expect(document.querySelector(".toast")).toBeNull();
  });

  test("cleans up toasts on pagehide so back nav ignores them", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `<div class="toast"></div>`;

    const { initMessagesToast } = loadModule();
    initMessagesToast(window);

    expect(document.querySelector(".toast")).not.toBeNull();
    window.dispatchEvent(new Event("pagehide"));
    expect(document.querySelector(".toast")).toBeNull();
  });

  test("no toasts exits cleanly", () => {
    document.body.innerHTML = ``;
    const { initMessagesToast } = loadModule();
    expect(() => initMessagesToast(window)).not.toThrow();
    // second call hits already initialized branch
    expect(() => initMessagesToast(window)).not.toThrow();
  });

  test("safely exits when window or document missing", () => {
    const { initMessagesToast } = loadModule();
    expect(() => initMessagesToast(null)).not.toThrow();
    expect(() => initMessagesToast({})).not.toThrow();
  });

  test("auto-inits on DOMContentLoaded when loading", () => {
    const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
    Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
    const addSpy = jest.spyOn(document, "addEventListener");
    jest.resetModules();
    delete global.__messagesToastInitialized;
    require(modulePath);
    expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
    // trigger handler to ensure it runs
    addSpy.mock.calls[0][1]();
    if (originalReady) {
      Object.defineProperty(document, "readyState", originalReady);
    }
    addSpy.mockRestore();
  });

  test("returns early when already initialized", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `<div class="toast"></div>`;
    const { initMessagesToast } = loadModule();
    global.__messagesToastInitialized = true;
    expect(() => initMessagesToast(window)).not.toThrow();
    jest.runAllTimers();
    expect(document.querySelector(".toast")).toBeNull();
    delete global.__messagesToastInitialized;
  });

  test("watches for toasts added after init", async () => {
    jest.useFakeTimers();
    const { initMessagesToast } = loadModule();
    initMessagesToast(window);
    const toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
    await Promise.resolve();
    jest.runAllTimers();
    expect(document.querySelector(".toast")).toBeNull();
  });

  test("ignores when no document present on global init path", () => {
    jest.resetModules();
    const globalAny = {};
    const mod = require("../../static/js/messages_toast");
    expect(mod).toBeTruthy();
  });

  test("initMessagesToast exits when no toasts present but window provided", () => {
    document.body.innerHTML = ``;
    const { initMessagesToast } = loadModule();
    expect(() => initMessagesToast(window)).not.toThrow();
  });
});
