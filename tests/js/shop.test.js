const { initShop } = require("../../static/js/shop");

function buildShopDom({ itemsHtml = '<div class="shop-masonry-item">Item</div>', hasNext = true } = {}) {
  const nextValue = hasNext ? "true" : "false";
  document.body.innerHTML = `
    <div id="shop-items-container" data-page="1" data-seed="abc" data-has-next="${nextValue}">
      ${itemsHtml}
    </div>
    <div id="shop-loading" class="d-none"></div>
    <div id="shop-sentinel"></div>
  `;
}

let originalFetch;
let originalIO;
let originalAdd;
let originalRemove;
let listeners = [];
let lastObserverCallback = null;

describe("shop", () => {
  beforeEach(setupShopEnv);
  afterEach(teardownShopEnv);
  testBuildsColumnsBasedOnBreakpoints();
  testTabletBreakpointColumnCount();
  testLargestBreakpointUsesSixColumns();
  testSmallWidthFallsBackToTwoColumns();
  testBuildColumnsRerunsOnResize();
  testBuildColumnsSkipsWhenBreakpointUnchanged();
  testUsesGlobalWindowFallback();
  testPlacesItemInShortestColumn();
});

function setupShopEnv() {
  document.body.innerHTML = "";
  originalFetch = global.fetch;
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ html: "", has_next: false })
  });
  originalIO = window.IntersectionObserver;
  window.IntersectionObserver = function (cb) {
    lastObserverCallback = cb;
    this.observe = jest.fn();
    this.disconnect = jest.fn();
  };
  originalAdd = window.addEventListener;
  originalRemove = window.removeEventListener;
  listeners = [];
  window.addEventListener = (type, fn, opts) => {
    listeners.push({ type, fn, opts });
    return originalAdd.call(window, type, fn, opts);
  };
  window.removeEventListener = (type, fn, opts) => originalRemove.call(window, type, fn, opts);
}

function teardownShopEnv() {
  global.fetch = originalFetch;
  window.IntersectionObserver = originalIO;
  listeners.forEach(({ type, fn, opts }) => {
    originalRemove.call(window, type, fn, opts);
  });
  window.addEventListener = originalAdd;
  window.removeEventListener = originalRemove;
  jest.clearAllMocks();
}

function testBuildsColumnsBasedOnBreakpoints() {
  test("builds columns based on breakpoints and places items", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item" id="a"></div><div class="shop-masonry-item" id="b"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1500, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(5);
    expect(document.querySelector(".shop-column .shop-masonry-item")).not.toBeNull();
  });
}

function testTabletBreakpointColumnCount() {
  test("breakpoint at tablet width yields expected column count", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 800, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(3);
  });
}

function testLargestBreakpointUsesSixColumns() {
  test("largest breakpoint uses six columns", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1700, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(6);
  });
}

function testSmallWidthFallsBackToTwoColumns() {
  test("small width falls back to two columns", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 100, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(2);
  });
}

function testBuildColumnsRerunsOnResize() {
  test("buildColumns re-runs on resize", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item" id="first"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1200, writable: true });
    initShop(window);
    const initial = document.querySelectorAll(".shop-column").length;
    Object.defineProperty(window, "innerWidth", { value: 400, writable: true });
    window.dispatchEvent(new window.Event("resize"));
    const updated = document.querySelectorAll(".shop-column").length;
    expect(updated).not.toBe(initial);
  });
}

function testBuildColumnsSkipsWhenBreakpointUnchanged() {
  test("buildColumns skips rebuild when breakpoint unchanged", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1600, writable: true });
    initShop(window);
    const initial = document.querySelectorAll(".shop-column").length;
    window.dispatchEvent(new window.Event("resize"));
    const after = document.querySelectorAll(".shop-column").length;
    expect(after).toBe(initial);
  });
}

function testUsesGlobalWindowFallback() {
  test("uses global window when no argument provided", () => {
    buildShopDom();
    expect(() => initShop()).not.toThrow();
  });
}

function testPlacesItemInShortestColumn() {
  test("places item in shortest column using heights", async () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div><div class="shop-masonry-item"></div>' });
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      return { observe: jest.fn(), disconnect: jest.fn() };
    });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="short-col"></div>', has_next: false })
    });
    initShop(window);
    const columns = document.querySelectorAll(".shop-column");
    Object.defineProperty(columns[0], "offsetHeight", { value: 10 });
    Object.defineProperty(columns[1], "offsetHeight", { value: 1 });
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("short-col")).not.toBeNull();
  });
}
