const modulePath = "../../static/js/messages_toast";

function loadModule() {
  jest.resetModules();
  delete global.__messagesToastInitialized;
  const mod = require(modulePath);
  delete global.__messagesToastInitialized;
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
    jest.useRealTimers();
  });

  test("falls back to class toggles without bootstrap", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `<div class="toast"></div>`;

    const { initMessagesToast } = loadModule();
    initMessagesToast(window);

    const toast = document.querySelector(".toast");
    expect(toast.classList.contains("show")).toBe(true);
    jest.runAllTimers();
    expect(toast.classList.contains("show")).toBe(false);
    expect(toast.classList.contains("hide")).toBe(true);
  });

  test("no toasts exits cleanly", () => {
    document.body.innerHTML = ``;
    const { initMessagesToast } = loadModule();
    expect(() => initMessagesToast(window)).not.toThrow();
    // second call hits already initialized branch
    expect(() => initMessagesToast(window)).not.toThrow();
  });
});
