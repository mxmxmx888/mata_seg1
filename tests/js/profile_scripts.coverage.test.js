const path = "../../static/js/profile_scripts";

describe("profile_scripts browser branches", () => {
  const originalWindow = global.window;
  const originalDocument = global.document;

  afterEach(() => {
    jest.resetModules();
    jest.restoreAllMocks();
    delete global.__PROFILE_SCRIPTS_BROWSER__;
    delete originalWindow.ProfileModals;
    delete originalWindow.ProfileInfinite;
    delete originalWindow.__profileScriptsInitialized;
    global.window = originalWindow;
    global.document = originalDocument;
  });

  test("falls back to browser globals and waits for DOMContentLoaded", () => {
    jest.resetModules();
    const initProfileModals = jest.fn(() => ({ deps: true }));
    const initProfileInfinite = jest.fn();
    const listeners = {};
    const readyStateSpy = jest.spyOn(originalDocument, "readyState", "get").mockReturnValue("loading");
    const addListenerSpy = jest.spyOn(originalDocument, "addEventListener").mockImplementation((event, cb) => {
      listeners[event] = cb;
    });
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    originalWindow.ProfileModals = { initProfileModals };
    originalWindow.ProfileInfinite = { initProfileInfinite };

    require(path);
    expect(listeners.DOMContentLoaded).toBeInstanceOf(Function);

    listeners.DOMContentLoaded();
    expect(initProfileModals).toHaveBeenCalledWith(global.window, global.window.document);
    expect(initProfileInfinite).toHaveBeenCalledWith(global.window, global.window.document, { deps: true });
    readyStateSpy.mockRestore();
    addListenerSpy.mockRestore();
  });

  test("skips modal deps and still initializes infinite with fallback deps", () => {
    jest.resetModules();
    const initProfileInfinite = jest.fn();
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    originalWindow.ProfileInfinite = { initProfileInfinite };

    require(path);

    expect(initProfileInfinite).toHaveBeenCalledWith(global.window, global.window.document, {});
  });

  test("handles missing infinite module without throwing", () => {
    jest.resetModules();
    const initProfileModals = jest.fn();
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    originalWindow.ProfileModals = { initProfileModals };

    require(path);

    expect(initProfileModals).toHaveBeenCalled();
  });

  test("initProfileScripts short-circuits when provided window lacks document", () => {
    jest.resetModules();
    const { initProfileScripts } = require(path);
    expect(() => initProfileScripts({})).not.toThrow();
  });

  test("auto init bails when global window is missing", () => {
    jest.resetModules();
    const savedWindow = global.window;
    const descriptor = Object.getOwnPropertyDescriptor(global, "window");
    Object.defineProperty(global, "window", { value: undefined, configurable: true, writable: true });

    expect(() => require(path)).not.toThrow();

    if (descriptor) {
      Object.defineProperty(global, "window", descriptor);
    } else {
      global.window = savedWindow;
    }
  });

  test("initProfileScripts skips when already initialized", () => {
    jest.resetModules();
    const { initProfileScripts } = require(path);
    expect(() => initProfileScripts(global.window)).not.toThrow();
    expect(() => initProfileScripts(global.window)).not.toThrow();
  });
});
