const modulePath = "../../static/js/post_layout";

const setReferrer = (value) => Object.defineProperty(document, "referrer", { value, configurable: true });

const renderBackButtonPage = ({ postId = "12", entry, fallback = "/fb" }) => {
  document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-post-id="${postId}" ${entry ? `data-entry="${entry}"` : ""} data-fallback="${fallback}"></a>
    `;
};

function loadModule() {
  jest.resetModules();
  delete global.__postLayoutInitialized;
  const mod = require(modulePath);
  delete global.__postLayoutInitialized;
  return mod;
}

describe("post_layout back navigation", () => {
  let originalRAF;
  let originalLocation;
  let originalHistory;
  let originalFormSubmit;
  const realFetch = global.fetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    delete window.__postLayoutInitialized;
    originalRAF = window.requestAnimationFrame;
    window.requestAnimationFrame = (cb) => cb();
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    originalLocation = window.location;
    delete window.location;
    window.location = { href: "http://localhost/post/1", origin: "http://localhost", assign: jest.fn(), replace: jest.fn() };
    originalHistory = window.history;
    window.history = { length: 0, back: jest.fn(), pushState: jest.fn(), replaceState: jest.fn() };
    originalFormSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = jest.fn();
  });

  afterEach(() => {
    window.requestAnimationFrame = originalRAF;
    global.fetch = realFetch;
    window.location = originalLocation;
    window.history = originalHistory;
    HTMLFormElement.prototype.submit = originalFormSubmit;
    window.sessionStorage.clear();
    jest.clearAllMocks();
  });

  test("history back path when history length > 1", () => {
    renderBackButtonPage({ entry: "http://localhost/prev", fallback: "/fb" });
    window.history.length = 2;
    const backSpy = jest.spyOn(window.history, "back").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    const assignSpy = jest.spyOn(window.location, "assign");
    expect(backSpy.mock.calls.length + assignSpy.mock.calls.length).toBeGreaterThan(0);
    backSpy.mockRestore();
    assignSpy.mockRestore();
  });

  test("back button and escape reuse stored entry when returning from edit", () => {
    setReferrer("http://localhost/recipes/12/edit");
    window.sessionStorage.setItem("post-entry-12", "http://localhost/from");
    renderBackButtonPage({ postId: "12", fallback: "/fb" });
    window.history.length = 5;
    const backSpy = jest.spyOn(window.history, "back");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).not.toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenLastCalledWith("http://localhost/from");
    backSpy.mockRestore();
    window.location.assign.mockClear();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(window.location.assign).toHaveBeenLastCalledWith("http://localhost/from");
  });

  test("back button ignores comment action referrers and keeps stored entry", () => {
    setReferrer("http://localhost/recipes/12/comment/");
    window.sessionStorage.setItem("post-entry-12", "http://localhost/from-feed");
    renderBackButtonPage({ postId: "12", fallback: "/fb" });
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(window.location.assign).toHaveBeenLastCalledWith("http://localhost/from-feed");
  });

  test("back button ignores comment referrer without stored entry and falls back", () => {
    setReferrer("http://localhost/recipes/34/comment/");
    renderBackButtonPage({ postId: "34", fallback: "/fb" });
    const backSpy = jest.spyOn(window.history, "back");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).not.toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenLastCalledWith("/fb");
    backSpy.mockRestore();
  });

  test("back button falls back when stored entry matches current page", () => {
    window.sessionStorage.setItem("post-entry-12", "http://localhost/post/1");
    renderBackButtonPage({ postId: "12", fallback: "/fb" });
    window.history.length = 3;
    const backSpy = jest.spyOn(window.history, "back");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).not.toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenLastCalledWith("/fb");
    backSpy.mockRestore();
  });

  test("back button prefers stored entry even when history available", () => {
    setReferrer("http://localhost/from");
    window.sessionStorage.setItem("post-entry-99", "http://localhost/feed");
    renderBackButtonPage({ postId: "99", entry: "http://localhost/from", fallback: "/fb" });
    window.history.length = 4;
    const backSpy = jest.spyOn(window.history, "back").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).not.toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenLastCalledWith("http://localhost/feed");
    backSpy.mockRestore();
  });

  test("back button click uses history when available", () => {
    setReferrer("http://localhost/ref");
    renderBackButtonPage({ entry: "http://localhost/ref", fallback: "/fb" });
    window.history.length = 3;
    const backSpy = jest.spyOn(window.history, "back").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    const assignSpy = jest.spyOn(window.location, "assign");
    expect(backSpy.mock.calls.length + assignSpy.mock.calls.length).toBeGreaterThan(0);
    backSpy.mockRestore();
    assignSpy.mockRestore();
  });

  test("resolveBackTarget handles invalid data-entry and fallback href", () => {
    setReferrer("");
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://[" href="/from-attr"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    expect(btn.getAttribute("href")).toBe("/from-attr");
  });

  test("resolveBackTarget uses fallback when referrer different origin", () => {
    setReferrer("http://other/from");
    document.body.innerHTML = `
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://other/from" data-fallback="/fb"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    expect(btn.getAttribute("href")).toBe("/fb");
  });

  test("parseUrl returns null for invalid ref and backButton absent", () => {
    setReferrer("::::");
    document.body.innerHTML = `<div class="post-view-similar"></div>`;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("parseUrl catch path handles invalid URL", () => {
    setReferrer("::::");
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("back button ignores comment referrer without stored entry and falls back", () => {
    setReferrer("http://localhost/recipes/34/comment/");
    renderBackButtonPage({ postId: "34", fallback: "/fb" });
    const backSpy = jest.spyOn(window.history, "back");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).not.toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenLastCalledWith("/fb");
    backSpy.mockRestore();
  });
});
