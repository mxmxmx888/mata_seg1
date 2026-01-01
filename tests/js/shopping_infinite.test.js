const modulePath = "../../static/js/shopping_infinite";
const { attachGlobal } = require("../../static/js/infinite_list");

const loadModule = () => {
  jest.resetModules();
  delete global.__shoppingInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__shoppingInfiniteInitialized;
  return mod;
};

const buildDom = (hasNext = true) => {
  document.body.innerHTML = `
    <div id="shopping-grid" data-page="1" data-shopping-has-next="${hasNext ? "true" : "false"}">
      <div class="shop-masonry-item" id="item1"></div>
    </div>
    <div id="shopping-sentinel"></div>
    <div id="shopping-loading" class="d-none"></div>
  `;
};

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const triggerScroll = () => window.dispatchEvent(new Event("scroll"));

const mockObserver = (html = '<div class="shop-masonry-item" id="newItem"></div>', hasNext = false) => {
  const observed = [];
  let triggerFn = () => {};
  let instance = null;
  const MockObserver = function (cb) {
    this.observe = (el) => observed.push(el);
    this.disconnect = jest.fn();
    triggerFn = (isIntersecting = true) => cb([{ isIntersecting }]);
    instance = this;
  };
  global.IntersectionObserver = MockObserver;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html, has_next: hasNext }) }));
  return { observed, trigger: (state = true) => triggerFn(state), instance };
};

beforeEach(() => {
  document.body.innerHTML = "";
  attachGlobal(window);
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="newItem"></div>', has_next: false }) }));
  delete global.__shoppingInfiniteInitialized;
});

afterEach(() => {
  delete global.IntersectionObserver;
  jest.clearAllMocks();
});

test("builds columns and loads more via observer", async () => {
  buildDom(true);
  const { observed, trigger, instance } = mockObserver();
  loadModule().initShoppingInfinite(window);
  expect(observed[0].id).toBe("shopping-sentinel");
  trigger();
  await flush();
  expect(document.getElementById("newItem")).not.toBeNull();
});

test("fallback scroll path triggers load", async () => {
  delete global.IntersectionObserver;
  buildDom(true);
  loadModule().initShoppingInfinite(window);
  window.innerHeight = 1000;
  Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
  window.scrollY = 0;
  triggerScroll();
  await flush();
  expect(document.getElementById("newItem")).not.toBeNull();
});

test("fetch error rolls back page", async () => {
  delete global.IntersectionObserver;
  buildDom(true);
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
  loadModule().initShoppingInfinite(window);
  triggerScroll();
  await flush();
  expect(document.getElementById("shopping-grid").dataset.page).toBe("1");
});

test("hasNext false prevents loading", () => {
  delete global.IntersectionObserver;
  buildDom(false);
  let captured;
  window.InfiniteList = { create: (opts) => { captured = opts; return null; } };
  loadModule().initShoppingInfinite(window);
  expect(captured.hasMore).toBe(false);
  expect(captured.nextPage).toBeNull();
});

test("no container or missing sentinel exits quietly", () => {
  document.body.innerHTML = ``;
  expect(() => loadModule().initShoppingInfinite(window)).not.toThrow();
  document.body.innerHTML = `<div id="shopping-grid"></div>`;
  expect(() => loadModule().initShoppingInfinite(window)).not.toThrow();
});

test("skips when already initialized and when window missing", () => {
  const { initShoppingInfinite } = loadModule();
  global.__shoppingInfiniteInitialized = true;
  expect(() => initShoppingInfinite(window)).not.toThrow();
  delete global.__shoppingInfiniteInitialized;
  expect(() => initShoppingInfinite(null)).not.toThrow();
});

test("rebuilds columns on resize when breakpoint changes", () => {
  buildDom(true);
  window.innerWidth = 1700;
  loadModule().initShoppingInfinite(window);
  const initialCols = document.querySelectorAll(".shop-column").length;
  window.innerWidth = 700;
  window.dispatchEvent(new Event("resize"));
  expect(document.querySelectorAll(".shop-column").length).not.toBe(initialCols);
});

test("falls back column count when innerWidth undefined", () => {
  buildDom(true);
  const originalInnerWidth = window.innerWidth;
  Object.defineProperty(window, "innerWidth", { value: undefined, writable: true });
  loadModule().initShoppingInfinite(window);
  expect(document.querySelectorAll(".shop-column").length).toBe(2);
  Object.defineProperty(window, "innerWidth", { value: originalInnerWidth, writable: true });
});

test("places new items into shortest column", async () => {
  delete global.IntersectionObserver;
  buildDom(true);
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="short-target"></div>', has_next: false }) }));
  loadModule().initShoppingInfinite(window);
  const cols = document.querySelectorAll(".shop-column");
  Object.defineProperty(cols[0], "offsetHeight", { value: 10 });
  Object.defineProperty(cols[1], "offsetHeight", { value: 1 });
  window.innerHeight = 1000;
  Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
  window.scrollY = 0;
  triggerScroll();
  await flush();
  expect(document.querySelector("#short-target").parentElement).toBe(cols[1]);
});

test("loading guard prevents double fetches", async () => {
  delete global.IntersectionObserver;
  let release;
  global.fetch = jest.fn(
    () =>
      new Promise((resolve) => {
        release = () => resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="guard"></div>', has_next: false }) });
      })
  );
  buildDom(true);
  loadModule().initShoppingInfinite(window);
  window.innerHeight = 1000;
  Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
  window.scrollY = 0;
  triggerScroll();
  release();
  await flush();
  expect(document.getElementById("guard")).not.toBeNull();
});

test("no loading element still runs without throwing", () => {
  delete global.IntersectionObserver;
  document.body.innerHTML = `
    <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
      <div class="shop-masonry-item"></div>
    </div>
    <div id="shopping-sentinel"></div>
  `;
  expect(() => loadModule().initShoppingInfinite(window)).not.toThrow();
  triggerScroll();
});
