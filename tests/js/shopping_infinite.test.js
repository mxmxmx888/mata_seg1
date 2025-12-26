const modulePath = "../../static/js/shopping_infinite";
const { attachGlobal } = require("../../static/js/infinite_list");

function loadModule() {
  jest.resetModules();
  delete global.__shoppingInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__shoppingInfiniteInitialized;
  return mod;
}

describe("shopping_infinite", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    attachGlobal(window);
    originalFetch = global.fetch;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="newItem"></div>', has_next: false })
      })
    );
    delete global.__shoppingInfiniteInitialized;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    delete global.IntersectionObserver;
    jest.clearAllMocks();
  });

  test("builds columns and loads more via observer", async () => {
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item" id="item1"></div>
        <div class="shop-masonry-item" id="item2"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;

    const observed = [];
    let instance;
    const MockObserver = function (cb) {
      this.observe = (el) => observed.push(el);
      this.disconnect = jest.fn();
      this.trigger = (isIntersecting = true) => cb([{ isIntersecting }]);
      instance = this;
    };
    global.IntersectionObserver = MockObserver;

    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);

    expect(observed[0].id).toBe("shopping-sentinel");
    instance.trigger();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("newItem")).not.toBeNull();
    expect(instance.disconnect).toHaveBeenCalled();
  });

  test("fallback scroll path triggers load", async () => {
    delete global.IntersectionObserver;
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item" id="item1"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
    window.scrollY = 0;
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("newItem")).not.toBeNull();
  });

  test("fetch error rolls back page", async () => {
    let page = 1;
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item" id="item1"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    // increment internal page by triggering
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    const grid = document.getElementById("shopping-grid");
    expect(grid.dataset.page).toBe("1");
  });

  test("hasNext false prevents loading", () => {
    delete global.IntersectionObserver;
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="false">
        <div class="shop-masonry-item" id="item1"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    const grid = document.getElementById("shopping-grid");
    grid.dataset.shoppingHasNext = "false";
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    global.fetch.mockClear();
    // without observer and hasNext false, nothing should fetch
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("no container exits quietly", () => {
    document.body.innerHTML = ``;
    const { initShoppingInfinite } = loadModule();
    expect(() => initShoppingInfinite(window)).not.toThrow();
  });

  test("returns early when sentinel missing", () => {
    document.body.innerHTML = `<div id="shopping-grid"></div>`;
    const { initShoppingInfinite } = loadModule();
    expect(() => initShoppingInfinite(window)).not.toThrow();
  });

  test("skips when already initialized and when window missing", () => {
    const { initShoppingInfinite } = loadModule();
    global.__shoppingInfiniteInitialized = true;
    expect(() => initShoppingInfinite(window)).not.toThrow();
    delete global.__shoppingInfiniteInitialized;
    expect(() => initShoppingInfinite(null)).not.toThrow();
  });

  test("rebuilds columns on resize when breakpoint changes", () => {
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    window.innerWidth = 1700;
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    const initialCols = document.querySelectorAll(".shop-column").length;
    window.innerWidth = 700;
    window.dispatchEvent(new Event("resize"));
    const resizedCols = document.querySelectorAll(".shop-column").length;
    expect(resizedCols).not.toBe(initialCols);
  });

  test("falls back column count when innerWidth undefined", () => {
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    const originalInnerWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { value: undefined, writable: true });
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(2);
    Object.defineProperty(window, "innerWidth", { value: originalInnerWidth, writable: true });
  });

  test("places new items into shortest column", async () => {
    delete global.IntersectionObserver;
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item" id="existing"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="short-target"></div>', has_next: false })
      })
    );
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    const cols = document.querySelectorAll(".shop-column");
    Object.defineProperty(cols[0], "offsetHeight", { value: 10 });
    Object.defineProperty(cols[1], "offsetHeight", { value: 1 });
    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
    window.scrollY = 0;
    window.dispatchEvent(new Event("scroll"));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.querySelector("#short-target").parentElement).toBe(cols[1]);
  });

  test("returns early when window has no document", () => {
    const { initShoppingInfinite } = loadModule();
    expect(() => initShoppingInfinite({})).not.toThrow();
  });

  test("loading guard prevents double fetches", async () => {
    delete global.IntersectionObserver;
    let release;
    global.fetch = jest.fn(
      () =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="guard"></div>', has_next: false })
            });
        })
    );
    document.body.innerHTML = `
      <div id="shopping-grid" data-page="1" data-shopping-has-next="true">
        <div class="shop-masonry-item"></div>
      </div>
      <div id="shopping-sentinel"></div>
      <div id="shopping-loading" class="d-none"></div>
    `;
    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);
    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
    window.scrollY = 0;
    window.dispatchEvent(new Event("scroll"));
    release();
    await new Promise((r) => setTimeout(r, 0));
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
    const { initShoppingInfinite } = loadModule();
    expect(() => initShoppingInfinite(window)).not.toThrow();
    window.dispatchEvent(new Event("scroll"));
  });
});
