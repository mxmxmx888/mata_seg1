const path = "../../static/js/profile_scripts";
const originalWindow = global.window;
const originalDocument = global.document;

describe("profile_scripts browser branches", () => {

  afterEach(resetProfileScriptsGlobals);
  testFallsBackToBrowserGlobals();
  testSkipsModalDepsWhenMissing();
  testHandlesMissingInfiniteModule();
  testInitShortCircuitsWithoutDocument();
  testAutoInitBailsWhenWindowMissing();
  testInitSkipsWhenAlreadyInitialized();
});

function resetProfileScriptsGlobals() {
  jest.resetModules();
  jest.restoreAllMocks();
  delete global.__PROFILE_SCRIPTS_BROWSER__;
  delete originalWindow.ProfileModals;
  delete originalWindow.ProfileInfinite;
  delete originalWindow.__profileScriptsInitialized;
  global.window = originalWindow;
  global.document = originalDocument;
}

function testFallsBackToBrowserGlobals() {
  test("falls back to browser globals and waits for DOMContentLoaded", () => {
    jest.resetModules();
    const initProfileModals = jest.fn(() => ({ deps: true }));
    const initProfileInfinite = jest.fn();
    const listeners = {};
    const readyStateSpy = jest.spyOn(global.document, "readyState", "get").mockReturnValue("loading");
    const addListenerSpy = jest.spyOn(global.document, "addEventListener").mockImplementation((event, cb) => {
      listeners[event] = cb;
    });
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    global.window.ProfileModals = { initProfileModals };
    global.window.ProfileInfinite = { initProfileInfinite };
    require(path);
    expect(listeners.DOMContentLoaded).toBeInstanceOf(Function);
    listeners.DOMContentLoaded();
    expect(initProfileModals).toHaveBeenCalledWith(global.window, global.window.document);
    expect(initProfileInfinite).toHaveBeenCalledWith(global.window, global.window.document, { deps: true });
    readyStateSpy.mockRestore();
    addListenerSpy.mockRestore();
  });
}

function testSkipsModalDepsWhenMissing() {
  test("skips modal deps and still initializes infinite with fallback deps", () => {
    jest.resetModules();
    const initProfileInfinite = jest.fn();
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    global.window.ProfileInfinite = { initProfileInfinite };
    require(path);
    expect(initProfileInfinite).toHaveBeenCalledWith(global.window, global.window.document, {});
  });
}

function testHandlesMissingInfiniteModule() {
  test("handles missing infinite module without throwing", () => {
    jest.resetModules();
    const initProfileModals = jest.fn();
    global.__PROFILE_SCRIPTS_BROWSER__ = true;
    global.window.ProfileModals = { initProfileModals };
    require(path);
    expect(initProfileModals).toHaveBeenCalled();
  });
}

function testInitShortCircuitsWithoutDocument() {
  test("initProfileScripts short-circuits when provided window lacks document", () => {
    jest.resetModules();
    const { initProfileScripts } = require(path);
    expect(() => initProfileScripts({})).not.toThrow();
  });
}

function testAutoInitBailsWhenWindowMissing() {
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
}

function testInitSkipsWhenAlreadyInitialized() {
  test("initProfileScripts skips when already initialized", () => {
    jest.resetModules();
    const { initProfileScripts } = require(path);
    expect(() => initProfileScripts(global.window)).not.toThrow();
    expect(() => initProfileScripts(global.window)).not.toThrow();
  });
}
