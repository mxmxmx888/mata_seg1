const modulePath = "../../static/js/post_layout";

const loadModule = () => {
  jest.resetModules();
  delete global.__postLayoutInitialized;
  const mod = require(modulePath);
  delete global.__postLayoutInitialized;
  return mod;
};

const render = (html = "") => {
  document.body.innerHTML = html;
};

const init = () => loadModule().initPostLayout(window);

const stubImg = (img, height, complete = true) => {
  Object.defineProperty(img, "complete", { value: complete });
  img.getBoundingClientRect = () => ({ height });
};

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

let originalRAF;
let originalLocation;
let originalHistory;
let originalFormSubmit;
const realFetch = global.fetch;

beforeEach(() => {
  render();
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

test("masonry builds on ready images and resize", () => {
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item"><img id="img1" /></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  stubImg(document.getElementById("img1"), 40);
  init();
  window.dispatchEvent(new Event("resize"));
  expect(document.querySelectorAll(".post-media-masonry-col").length).toBeGreaterThan(0);
});

test("masonry rebuilds on image load/error when not complete", () => {
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item"><img id="img1" /></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  const img = document.getElementById("img1");
  stubImg(img, 30, false);
  const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
  init();
  img.dispatchEvent(new Event("load"));
  img.dispatchEvent(new Event("error"));
  expect(document.querySelectorAll(".post-media-masonry-col").length).toBeGreaterThan(0);
  rafSpy.mockRestore();
});

test("masonry balances columns with InfiniteList present", () => {
  window.InfiniteList = { placeInColumns: jest.fn() };
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item"><img id="tall" /></div>
      <div class="post-media-masonry-item"><img id="short" /></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  stubImg(document.getElementById("tall"), 200);
  stubImg(document.getElementById("short"), 20);
  init();
  const cols = document.querySelectorAll(".post-media-masonry-col");
  expect(cols[0].children.length).toBe(1);
  expect(cols[1].children.length).toBe(1);
  delete window.InfiniteList;
});

test("masonry uses single visible column on narrow viewports", () => {
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item" id="item1"><div class="inner"></div></div>
      <div class="post-media-masonry-item" id="item2"><div class="inner"></div></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  window.innerWidth = 500;
  document.querySelectorAll(".post-media-masonry-item").forEach((item) => (item.getBoundingClientRect = () => ({ height: 5 })));
  init();
  const cols = document.querySelectorAll(".post-media-masonry-col");
  expect(cols.length).toBe(2);
  expect(cols[1].style.display).toBe("none");
});

test("masonry builds when rAF missing using setTimeout and ResizeObserver", () => {
  const originalTimeout = window.setTimeout;
  window.requestAnimationFrame = undefined;
  window.setTimeout = jest.fn((cb) => cb());
  const observeSpy = jest.fn();
  window.ResizeObserver = jest.fn().mockImplementation(() => ({ observe: observeSpy }));
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item"><img id="a" /></div>
      <div class="post-media-masonry-item"><img id="b" /></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  stubImg(document.getElementById("a"), 60);
  stubImg(document.getElementById("b"), 30);
  init();
  expect(window.setTimeout).toHaveBeenCalled();
  expect(observeSpy).toHaveBeenCalled();
  window.setTimeout = originalTimeout;
  delete window.ResizeObserver;
});

test("handleScroll returns early when primary or similar missing", () => {
  render(`<div class="post-view-similar"></div>`);
  init();
  expect(() => window.dispatchEvent(new Event("scroll"))).not.toThrow();
});

test("like form parseCount handles NaN and clamps", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
  render(`
    <form data-like-form action="/like">
      <input name="csrfmiddlewaretoken" value="token" />
      <button data-like-toggle data-liked="true"><i></i></button>
      <span data-like-count>not-a-number</span>
    </form>
  `);
  init();
  document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(document.querySelector("[data-like-count]").textContent).toBe("0");
});

test("handles window without document", () => {
  const { initPostLayout } = loadModule();
  expect(() => initPostLayout({})).not.toThrow();
});

test("sessionStorage errors are handled resolving back target", () => {
  render(`
    <div id="post-primary"></div>
    <div class="post-view-similar"></div>
    <a class="post-back-button" data-post-id="err" data-entry="http://localhost/from" data-fallback="/fb"></a>
  `);
  const originalStorage = window.sessionStorage;
  window.sessionStorage = { getItem: () => { throw new Error("boom"); }, setItem: jest.fn(), clear: jest.fn() };
  const assignSpy = jest.spyOn(window.location, "assign");
  init();
  document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
  expect(assignSpy).toHaveBeenCalled();
  window.sessionStorage = originalStorage;
  assignSpy.mockRestore();
});

test("back hint visibility without rAF observes gallery", () => {
  window.requestAnimationFrame = undefined;
  const observeSpy = jest.fn();
  window.ResizeObserver = jest.fn().mockImplementation(() => ({ observe: observeSpy }));
  render(`
    <div id="post-primary"></div>
    <div class="post-view-similar"></div>
    <a class="post-back-button"></a>
    <div class="recipe-gallery"></div>
  `);
  const back = document.querySelector(".post-back-button");
  const gallery = document.querySelector(".recipe-gallery");
  back.getBoundingClientRect = () => ({ top: 10, bottom: 20, right: 5 });
  gallery.getBoundingClientRect = () => ({ top: 15, bottom: 100, left: 40 });
  init();
  expect(back.classList.contains("post-back-button--hide-hint")).toBe(false);
  expect(observeSpy).toHaveBeenCalledWith(gallery);
  delete window.ResizeObserver;
});

test("auto init waits for DOMContentLoaded when loading", () => {
  const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
  Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
  const addSpy = jest.spyOn(document, "addEventListener");
  jest.resetModules();
  delete global.__postLayoutInitialized;
  require("../../static/js/post_layout");
  expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
  addSpy.mock.calls[0][1]();
  if (originalReady) Object.defineProperty(document, "readyState", originalReady);
  addSpy.mockRestore();
});
