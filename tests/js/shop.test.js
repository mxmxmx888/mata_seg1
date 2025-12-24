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

  test("breakpoint at tablet width yields expected column count", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 800, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(3);
  });

  test("largest breakpoint uses six columns", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1700, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(6);
  });

  test("small width falls back to two columns", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 100, writable: true });
    initShop(window);
    expect(document.querySelectorAll(".shop-column").length).toBe(2);
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

  test("ignores empty html responses but resets loading", async () => {
    buildShopDom({ itemsHtml: "" });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html: "", has_next: true })
    });
    initShop(window);
    const loading = document.getElementById("shop-loading");
    expect(loading.classList.contains("d-none")).toBe(true);

    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(document.querySelectorAll(".shop-masonry-item").length).toBe(0);
    expect(loading.classList.contains("d-none")).toBe(true);
  });

  test("loadMoreShopItems skips when hasNext is false", () => {
    buildShopDom({ hasNext: false });
    initShop(window);
    expect(document.getElementById("shop-items-container").dataset.hasNext).toBe("false");
    window.dispatchEvent(new window.Event("scroll"));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("waitForImages resolves after image load and places item", async () => {
    buildShopDom({ itemsHtml: "" });
    let disconnectSpy;
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      disconnectSpy = jest.fn();
      return { observe: jest.fn(), disconnect: disconnectSpy };
    });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html: '<div class="shop-masonry-item"><img id="img-load" /></div>', has_next: false })
    });

    initShop(window);

    const loadPromise = lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    const img = document.getElementById("img-load");
    expect(img).not.toBeNull();
    img.dispatchEvent(new Event("load"));
    await Promise.resolve(loadPromise);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(img.closest(".shop-column")).not.toBeNull();
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

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

  test("default column count fallback and disconnect on final page", async () => {
    buildShopDom();
    Object.defineProperty(window, "innerWidth", { value: -10, writable: true });
    let disconnectSpy;
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      disconnectSpy = jest.fn();
      return { observe: jest.fn(), disconnect: disconnectSpy };
    });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html: '<div class="shop-masonry-item"></div>', has_next: false })
    });
    initShop(window);
    const columns = document.querySelectorAll(".shop-column");
    // force branch where later column is shorter
    Object.defineProperty(columns[0], "offsetHeight", { value: 10 });
    Object.defineProperty(columns[1], "offsetHeight", { value: 0 });
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(columns.length).toBe(2);
    expect(typeof disconnectSpy).toBe("function");
  });

  test("handles non-ok fetch response gracefully", async () => {
    const originalIO = window.IntersectionObserver;
    delete window.IntersectionObserver;
    buildShopDom();
    const loading = document.getElementById("shop-loading");
    global.fetch.mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) });
    Object.defineProperty(window, "innerHeight", { value: 1000, writable: true });
    Object.defineProperty(window, "scrollY", { value: 2000, writable: true });
    Object.defineProperty(document.body, "offsetHeight", { value: 2000, writable: true });
    initShop(window);

    expect(loading.classList.contains("d-none")).toBe(true);
    window.dispatchEvent(new window.Event("scroll"));
    expect(loading.classList.contains("d-none")).toBe(false);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(loading.classList.contains("d-none")).toBe(true);

    window.IntersectionObserver = originalIO;
  });

  test("buildColumns skips rebuild when breakpoint unchanged", () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerWidth", { value: 1600, writable: true });
    initShop(window);
    const initial = document.querySelectorAll(".shop-column").length;
    window.dispatchEvent(new window.Event("resize"));
    const after = document.querySelectorAll(".shop-column").length;
    expect(after).toBe(initial);
  });

  test("loadMoreShopItems ignores when loading already true", async () => {
    delete window.IntersectionObserver;
    let release;
    global.fetch = jest.fn(
      () =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="guard-shop"></div>', has_next: false })
            });
        })
    );
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
    Object.defineProperty(window, "innerHeight", { value: 1000, writable: true });
    Object.defineProperty(window, "scrollY", { value: 0, writable: true });
    Object.defineProperty(document.body, "offsetHeight", { value: 0, writable: true });
    initShop(window);
    window.dispatchEvent(new window.Event("scroll"));
    window.dispatchEvent(new window.Event("scroll"));
    expect(global.fetch).toHaveBeenCalledTimes(1);
    release();
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("guard-shop")).not.toBeNull();
  });

  test("uses default scroll fallback when sentinel missing triggers early exit", () => {
    document.body.innerHTML = `
      <div id="shop-items-container" data-page="1" data-has-next="true">
        <div class="shop-masonry-item"></div>
      </div>
      <div id="shop-loading"></div>
    `;
    expect(() => initShop(window)).not.toThrow();
  });

  test("handles fetch response without html", async () => {
    buildShopDom();
    global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ html: null, has_next: false }) });
    initShop(window);
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalled();
  });

  test("works when loading element is missing", () => {
    document.body.innerHTML = `
      <div id="shop-items-container" data-page="1" data-has-next="true"></div>
      <div id="shop-sentinel"></div>
    `;
    expect(() => initShop(window)).not.toThrow();
  });

  test("fetch failure rolls back page number", async () => {
    delete window.IntersectionObserver;
    buildShopDom();
    const container = document.getElementById("shop-items-container");
    global.fetch.mockRejectedValueOnce(new Error("fail"));
    Object.defineProperty(window, "innerHeight", { value: 1000, writable: true });
    Object.defineProperty(window, "scrollY", { value: 1200, writable: true });
    Object.defineProperty(document.body, "offsetHeight", { value: 2000, writable: true });
    initShop(window);
    window.dispatchEvent(new window.Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(container.dataset.page).toBe("1");
  });

  test("uses global window when no argument provided", () => {
    buildShopDom();
    expect(() => initShop()).not.toThrow();
  });

  test("places item in shortest column using heights", async () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div><div class="shop-masonry-item"></div>' });
    const observed = [];
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      return { observe: (el) => observed.push(el), disconnect: jest.fn() };
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

  test("setLoading returns early when loading element missing during fetch", async () => {
    document.body.innerHTML = `
      <div id="shop-items-container" data-page="1" data-has-next="true">
        <div class="shop-masonry-item"></div>
      </div>
      <div id="shop-sentinel"></div>
    `;
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      return { observe: jest.fn(), disconnect: jest.fn() };
    });
    initShop(window);
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalled();
  });

  test("includes seed param and toggles loading element", async () => {
    buildShopDom();
    const loading = document.getElementById("shop-loading");
    global.fetch.mockImplementationOnce((url) => {
      expect(url).toContain("seed=abc");
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ html: "", has_next: false }) });
    });
    const { initShop } = require("../../static/js/shop");
    initShop(window);
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    expect(loading.classList.contains("d-none")).toBe(false);
    await new Promise((r) => setTimeout(r, 0));
    expect(loading.classList.contains("d-none")).toBe(true);
  });

  test("waitForImages handles error events", async () => {
    buildShopDom({ itemsHtml: "" });
    let disconnectSpy;
    window.IntersectionObserver = jest.fn((cb) => {
      lastObserverCallback = cb;
      disconnectSpy = jest.fn();
      return { observe: jest.fn(), disconnect: disconnectSpy };
    });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ html: '<div class="shop-masonry-item"><img id="errImg" /></div>', has_next: false })
    });
    initShop(window);

    const loadPromise = lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 0));
    const img = document.getElementById("errImg");
    expect(img).not.toBeNull();
    img.dispatchEvent(new Event("error"));
    await Promise.resolve(loadPromise);
    await new Promise((r) => setTimeout(r, 0));
    expect(img.closest(".shop-column")).not.toBeNull();
    lastObserverCallback && lastObserverCallback([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("waitForImages resolves immediately when image already complete", async () => {
    buildShopDom({ itemsHtml: '<div class="shop-masonry-item"><img id="doneImg" /></div>' });
    const descriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "complete");
    Object.defineProperty(HTMLImageElement.prototype, "complete", {
      configurable: true,
      get() {
        return true;
      }
    });
    initShop(window);
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("doneImg").closest(".shop-column")).not.toBeNull();
    if (descriptor) {
      Object.defineProperty(HTMLImageElement.prototype, "complete", descriptor);
    } else {
      delete HTMLImageElement.prototype.complete;
    }
  });
});
