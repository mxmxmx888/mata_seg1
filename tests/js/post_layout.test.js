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

const setReferrer = (url) => {
  Object.defineProperty(document, "referrer", { value: url, configurable: true });
};

const setHistoryLength = (len) => {
  Object.defineProperty(window.history, "length", { value: len, configurable: true });
};

const stubImgComplete = (img, height) => {
  Object.defineProperty(img, "complete", { value: true });
  img.getBoundingClientRect = () => ({ height });
};

let originalRAF;
let originalLocation;
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
  originalFormSubmit = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = jest.fn();
});

afterEach(() => {
  window.requestAnimationFrame = originalRAF;
  global.fetch = realFetch;
  window.location = originalLocation;
  HTMLFormElement.prototype.submit = originalFormSubmit;
  jest.clearAllMocks();
});

test("builds masonry columns and distributes items", () => {
  render(`
    <div class="post-media-masonry">
      <div class="post-media-masonry-item" id="item1"><img /></div>
      <div class="post-media-masonry-item" id="item2"><img /></div>
    </div>
  `);
  const imgs = document.querySelectorAll(".post-media-masonry-item img");
  stubImgComplete(imgs[0], 100);
  stubImgComplete(imgs[1], 10);
  init();
  const cols = document.querySelectorAll(".post-media-masonry-col");
  expect(cols.length).toBe(2);
  expect(cols[0].children.length + cols[1].children.length).toBe(2);
});

test("sets similar grid column CSS variable based on width", () => {
  const grid = document.createElement("div");
  grid.className = "view-similar-grid";
  Object.defineProperty(grid, "clientWidth", { value: 300 });
  document.body.appendChild(grid);
  init();
  expect(grid.style.getPropertyValue("--similar-cols")).not.toBe("");
});

test("escape key triggers back even when handled or legacy key", () => {
  render(`<a class="post-back-button" data-fallback="/fallback"></a>`);
  init();
  const e1 = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
  e1.preventDefault();
  document.dispatchEvent(e1);
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Esc" }));
  expect(window.location.assign).toHaveBeenCalledWith("/fallback");
});

test("escape key works when modal or lightbox open", () => {
  render(`
    <div class="modal show"></div>
    <div class="pswp--open"></div>
    <a class="post-back-button" data-fallback="/fallback"></a>
  `);
  const assignSpy = jest.spyOn(window.location, "assign");
  init();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  expect(assignSpy).toHaveBeenCalledWith("/fallback");
  assignSpy.mockRestore();
});

test("like form short-circuits when fetch undefined or csrf missing", () => {
  delete global.fetch;
  render(`<form data-like-form action="/like"><button data-like-toggle data-liked="false"></button></form>`);
  init();
  expect(() => document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
});

test("like form handles non-ok by submitting natively", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  render(`
    <form data-like-form action="/like">
      <input type="hidden" name="csrfmiddlewaretoken" value="token" />
      <button data-like-toggle data-liked="false" data-count="1"><i></i></button>
      <span data-like-count>1</span>
    </form>
  `);
  const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit");
  init();
  document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
  await Promise.resolve();
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("like form toggles state on fetch success", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
  render(`
    <form data-like-form action="/like">
      <input type="hidden" name="csrfmiddlewaretoken" value="token" />
      <button data-like-toggle data-liked="false" data-count="1"><i></i></button>
      <span data-like-count>1</span>
    </form>
  `);
  init();
  document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
  await Promise.resolve();
  expect(document.querySelector("[data-like-toggle]").dataset.liked).toBe("true");
  expect(document.querySelector("[data-like-count]").textContent).toBe("2");
});

test("back button uses referrer when history not available", () => {
  setHistoryLength(1);
  setReferrer("http://localhost/from");
  render(`<a class="post-back-button" data-entry="http://localhost/from" data-fallback="/fallback"></a>`);
  init();
  document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
  expect(window.location.assign).toHaveBeenCalledWith("http://localhost/from");
});

test("back button prefers history when different from current, else fallback", () => {
  setReferrer("http://localhost/post/1");
  setHistoryLength(2);
  render(`<a class="post-back-button" data-entry="http://localhost/post/1" data-fallback="/fallback"></a>`);
  const backSpy = jest.spyOn(window.history, "back");
  init();
  document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
  expect(backSpy).not.toHaveBeenCalled();
  expect(window.location.assign).toHaveBeenLastCalledWith("/fallback");
  backSpy.mockRestore();
});

test("cameFromCreate popstate redirects to fallback", () => {
  setReferrer("http://localhost/recipes/create");
  render(`<a class="post-back-button" data-entry="http://localhost/from" data-fallback="/fallback"></a>`);
  init();
  window.dispatchEvent(new PopStateEvent("popstate", { state: { cameFromCreate: true } }));
  expect(window.location.replace).toHaveBeenCalledWith("/fallback");
});

test("handleScroll sets fade amount", () => {
  render(`
    <div id="post-primary" class="post-primary">
      <div class="post-primary-img"><img /></div>
    </div>
    <div class="post-view-similar"></div>
  `);
  window.scrollY = 10;
  const primary = document.querySelector(".post-primary");
  const setPropertySpy = jest.spyOn(primary.style, "setProperty");
  init();
  window.dispatchEvent(new Event("scroll"));
  expect(setPropertySpy).toHaveBeenCalledWith("--post-fade-amount", expect.any(String));
  setPropertySpy.mockRestore();
});
