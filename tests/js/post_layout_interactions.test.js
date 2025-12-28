const modulePath = "../../static/js/post_layout";

function loadModule() {
  jest.resetModules();
  delete global.__postLayoutInitialized;
  const mod = require(modulePath);
  delete global.__postLayoutInitialized;
  return mod;
}

function mockRect(el, height) {
  el.getBoundingClientRect = () => ({ height });
}

describe("post_layout interactions", () => {
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
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://localhost/prev" data-fallback="/fb"></a>
    `;
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
    Object.defineProperty(document, "referrer", { value: "http://localhost/recipes/12/edit", configurable: true });
    window.sessionStorage.setItem("post-entry-12", "http://localhost/from");
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-post-id="12" data-fallback="/fb"></a>
    `;
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

  test("parseUrl returns null for invalid ref and backButton absent", () => {
    Object.defineProperty(document, "referrer", { value: "::::", configurable: true });
    document.body.innerHTML = `
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("masonry requestMasonry path when media complete and resize listener", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = masonry.querySelector("img");
    img.complete = true;
    mockRect(img, 40);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    window.dispatchEvent(new Event("resize"));
    const cols = masonry.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("media load listener requests masonry when not complete", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img id="img1" /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = document.getElementById("img1");
    Object.defineProperty(img, "complete", { value: false });
    mockRect(img, 30);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    img.dispatchEvent(new Event("load"));
    expect(masonry.querySelectorAll(".post-media-masonry-col").length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("back button click uses history when available", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/ref", configurable: true });
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://localhost/ref"></a>
    `;
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

  test("parseUrl catch path handles invalid URL", () => {
    Object.defineProperty(document, "referrer", { value: "::::", configurable: true });
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("resolveBackTarget handles invalid data-entry and fallback href", () => {
    Object.defineProperty(document, "referrer", { value: "", configurable: true });
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

  test("handles media load events to rebuild masonry", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = masonry.querySelector("img");
    img.complete = false;
    mockRect(img, 50);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    img.dispatchEvent(new Event("load"));
    const cols = masonry.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("balances columns even when global InfiniteList is present", () => {
    window.InfiniteList = { placeInColumns: jest.fn() };
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item"><img id="tall" /></div>
        <div class="post-media-masonry-item"><img id="short" /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    mockRect(document.getElementById("tall"), 200);
    mockRect(document.getElementById("short"), 20);
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const cols = document.querySelectorAll(".post-media-masonry-col");
    expect(cols[0].children.length).toBe(1);
    expect(cols[1].children.length).toBe(1);
    delete window.InfiniteList;
  });

  test("gracefully exits when no masonry or similar grids", () => {
    document.body.innerHTML = `
      <div id="post-primary"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("uses one masonry column when only one item on wide screens", () => {
    const originalWidth = window.innerWidth;
    window.innerWidth = 1200;
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item"><img id="solo-img" /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const img = document.getElementById("solo-img");
    img.complete = true;
    mockRect(img, 40);
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const cols = document.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBe(2);
    expect(cols[1].style.display).toBe("none");
    window.innerWidth = originalWidth;
  });

  test("rebuilds masonry when media fires error", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item"><img id="err-img" /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const img = document.getElementById("err-img");
    Object.defineProperty(img, "complete", { value: false });
    mockRect(img, 25);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    rafSpy.mockClear();
    img.dispatchEvent(new Event("error"));
    expect(rafSpy).toHaveBeenCalled();
    rafSpy.mockRestore();
  });

  test("handles narrow viewport with single masonry column and no media rect", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><div class="inner"></div></div>
        <div class="post-media-masonry-item" id="item2"><div class="inner"></div></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    window.innerWidth = 500;
    const items = document.querySelectorAll(".post-media-masonry-item");
    items.forEach((item) => {
      item.getBoundingClientRect = () => ({ height: 5 });
    });
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const cols = document.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBe(2);
    expect(cols[1].style.display).toBe("none");
  });

  test("handleScroll returns early when primary or similar missing", () => {
    document.body.innerHTML = `<div class="post-view-similar"></div>`;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    expect(() => window.dispatchEvent(new Event("scroll"))).not.toThrow();
  });

  test("resolveBackTarget uses fallback when referrer different origin", () => {
    Object.defineProperty(document, "referrer", { value: "http://other/from", configurable: true });
    document.body.innerHTML = `
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://other/from" data-fallback="/fb"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    expect(btn.getAttribute("href")).toBe("/fb");
  });

  test("like form parseCount handles NaN and clamps count", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="true"><i class="bi-heart-fill"></i></button>
        <span data-like-count>not-a-number</span>
      </form>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const form = document.querySelector("[data-like-form]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.querySelector("[data-like-count]").textContent).toBe("0");
  });

  test("early return when window lacks document", () => {
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout({})).not.toThrow();
  });
});
