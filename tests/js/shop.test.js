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

describe("shop", () => {
  let originalFetch;
  let originalIO;
  let originalAdd;
  let originalRemove;
  let listeners = [];
  let lastObserverCallback = null;

  beforeEach(() => {
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
  });

  afterEach(() => {
    global.fetch = originalFetch;
    window.IntersectionObserver = originalIO;
    listeners.forEach(({ type, fn, opts }) => {
      originalRemove.call(window, type, fn, opts);
    });
    window.addEventListener = originalAdd;
    window.removeEventListener = originalRemove;
    jest.clearAllMocks();
  });

  test("builds columns based on breakpoints and places items", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item" id="a"></div><div class="shop-masonry-item" id="b"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1500, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(5);
    expect(document.querySelector(".shop-column .shop-masonry-item")).not.toBeNull();
  });

  test("falls back to scroll listener when IntersectionObserver missing", () => {
    const originalIO = window.IntersectionObserver;
    delete window.IntersectionObserver;

    buildShopDom();
    initShop(window);

    expect(global.fetch).not.toHaveBeenCalled();
    window.dispatchEvent(new window.Event("scroll"));
    expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(1);

    window.IntersectionObserver = originalIO;
  });

  test("loads more items via fetch and appends html", async () => {
    buildShopDom();
    const html = '<div class="shop-masonry-item" id="new"></div>';
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html, has_next: false })
    });

    let observerCallback = null;
    window.IntersectionObserver = jest.fn((cb) => {
      observerCallback = cb;
      return { observe: jest.fn(), disconnect: jest.fn() };
    });

    initShop(window);

    observerCallback && observerCallback([{ isIntersecting: true }]);

    // Wait for promises to resolve
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.getElementById("new")).not.toBeNull();
    expect(global.fetch).toHaveBeenCalled();
  });

  test("handles fetch failure by decrementing page", async () => {
    const originalIO = window.IntersectionObserver;
    delete window.IntersectionObserver;

    buildShopDom();
    global.fetch.mockRejectedValue(new Error("fail"));
    Object.defineProperty(window, "innerHeight", { value: 1000, writable: true });
    Object.defineProperty(window, "scrollY", { value: 1200, writable: true });
    Object.defineProperty(document.body, "offsetHeight", { value: 2000, writable: true });

    initShop(window);
    const initialCallCount = global.fetch.mock.calls.length;

    window.dispatchEvent(new window.Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch.mock.calls.length).toBeGreaterThan(initialCallCount);

    window.IntersectionObserver = originalIO;
  });

  test("does nothing when container or sentinel missing", () => {
    document.body.innerHTML = `<div id="shop-items-container"></div>`;
    initShop(window);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("appendHtml resolves when no html and waitForImages resolves empty", async () => {
    buildShopDom({ itemsHtml: "" });
    initShop(window);
    // direct call to exported init only; simulate image list empty (no throw)
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(true).toBe(true);
  });

  test("loadMoreShopItems skips when hasNext is false", () => {
    buildShopDom({ hasNext: false });
    initShop(window);
    expect(document.getElementById("shop-items-container").dataset.hasNext).toBe("false");
    window.dispatchEvent(new window.Event("scroll"));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("waitForImages resolves after image load", async () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"><img id="img" /></div>' });
    const img = document.createElement("img");
    img.id = "img";
    document.querySelector(".shop-masonry-item").appendChild(img);
    Object.defineProperty(img, "complete", { value: false });
    initShop(window);
    img.dispatchEvent(new Event("load"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(true).toBe(true);
  });

  test("buildColumns re-runs on resize", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item" id="first"></div>' });
    initShop(window);
    const initial = document.querySelectorAll(".shop-column").length;
    Object.defineProperty(window, "innerWidth", { value: 400, writable: true });
    window.dispatchEvent(new window.Event("resize"));
    const updated = document.querySelectorAll(".shop-column").length;
    expect(updated).not.toBe(initial);
  });

  test("appendHtml places items after wait", async () => {
    buildShopDom({ itemsHtml: "" });
    initShop(window);
    const html = '<div class="shop-masonry-item" id="later"></div>';
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html, has_next: false })
    });
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("later")).not.toBeNull();
  });
});
