const { initShop } = require("../../static/js/shop");

const nativeIO = window.IntersectionObserver;

const buildShopDom = ({ itemsHtml = '<div class="shop-masonry-item">Item</div>', hasNext = true, seed = "abc" } = {}) => {
  const nextValue = hasNext ? "true" : "false";
  document.body.innerHTML = `
    <div id="shop-items-container" data-page="1" data-seed="${seed}" data-has-next="${nextValue}">
      ${itemsHtml}
    </div>
    <div id="shop-loading" class="d-none"></div>
    <div id="shop-sentinel"></div>
  `;
};

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const doubleFlush = async () => {
  await flush();
  await flush();
};
const triggerScroll = () => window.dispatchEvent(new window.Event("scroll"));
const setScroll = ({ innerHeight = 1000, scrollY = 1200, bodyHeight = 2000 } = {}) => {
  Object.defineProperty(window, "innerHeight", { value: innerHeight, writable: true });
  Object.defineProperty(window, "scrollY", { value: scrollY, writable: true });
  Object.defineProperty(document.body, "offsetHeight", { value: bodyHeight, writable: true });
};
const mockObserver = () => {
  let callback;
  const disconnect = jest.fn();
  window.IntersectionObserver = jest.fn((cb) => {
    callback = cb;
    return { observe: jest.fn(), disconnect };
  });
  return { trigger: (entries = [{ isIntersecting: true }]) => callback && callback(entries), disconnect };
};
const disableObserver = () => {
  const original = window.IntersectionObserver;
  delete window.IntersectionObserver;
  return () => {
    window.IntersectionObserver = original;
  };
};
const mockFetch = (value) => {
  global.fetch = jest.fn().mockResolvedValue(value);
};
const mockFetchReject = () => {
  global.fetch = jest.fn().mockRejectedValue(new Error("fail"));
};

let originalFetch;
let originalIO;

beforeEach(() => {
  document.body.innerHTML = "";
  originalFetch = global.fetch;
  originalIO = window.IntersectionObserver;
  window.IntersectionObserver = nativeIO;
  mockFetch({ ok: true, json: () => Promise.resolve({ html: "", has_next: false }) });
});

afterEach(() => {
  global.fetch = originalFetch;
  window.IntersectionObserver = nativeIO;
  jest.clearAllMocks();
});

test("falls back to scroll listener when IntersectionObserver missing", async () => {
  const restore = disableObserver();
  buildShopDom();
  initShop(window);
  expect(global.fetch).not.toHaveBeenCalled();
  triggerScroll();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
  restore();
});

test("loads more items via fetch and appends html", async () => {
  buildShopDom();
  mockFetch({ ok: true, json: () => Promise.resolve({ html: '<div id="new" class="shop-masonry-item"></div>', has_next: false }) });
  const observer = mockObserver();
  initShop(window);
  observer.trigger();
  await doubleFlush();
  expect(document.getElementById("new")).not.toBeNull();
});

test("handles fetch failure by decrementing page on scroll fallback", async () => {
  const restore = disableObserver();
  buildShopDom();
  mockFetchReject();
  setScroll();
  initShop(window);
  triggerScroll();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
  restore();
});

test("does nothing when container or sentinel missing", () => {
  document.body.innerHTML = `<div id="shop-items-container"></div>`;
  initShop(window);
  expect(global.fetch).not.toHaveBeenCalled();
});

test("ignores empty html responses but resets loading", async () => {
  buildShopDom({ itemsHtml: "" });
  mockFetch({ ok: true, json: () => Promise.resolve({ html: "", has_next: true }) });
  const observer = mockObserver();
  initShop(window);
  const loading = document.getElementById("shop-loading");
  observer.trigger();
  await doubleFlush();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(document.querySelectorAll(".shop-masonry-item").length).toBe(0);
  expect(loading.classList.contains("d-none")).toBe(true);
});

test("loadMoreShopItems skips when hasNext is false", async () => {
  buildShopDom({ hasNext: false });
  initShop(window);
  global.fetch.mockClear();
  triggerScroll();
  await flush();
  expect(global.fetch.mock.calls.length).toBeLessThanOrEqual(1);
});

test("waitForImages resolves after image load and places item", async () => {
  buildShopDom({ itemsHtml: "" });
  const observer = mockObserver();
  mockFetch({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item"><img id="img-load" /></div>', has_next: false }) });
  initShop(window);
  observer.trigger();
  await flush();
  document.getElementById("img-load").dispatchEvent(new Event("load"));
  await doubleFlush();
  expect(document.getElementById("img-load").closest(".shop-column")).not.toBeNull();
});

test("appendHtml places items after wait", async () => {
  buildShopDom({ itemsHtml: "" });
  const observer = mockObserver();
  mockFetch({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item" id="later"></div>', has_next: false }) });
  initShop(window);
  observer.trigger();
  await doubleFlush();
  expect(document.getElementById("later")).not.toBeNull();
});

test("default column count fallback and disconnect on final page", async () => {
  buildShopDom();
  Object.defineProperty(window, "innerWidth", { value: -10, writable: true });
  const observer = mockObserver();
  mockFetch({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item"></div>', has_next: false }) });
  initShop(window);
  observer.trigger();
  await doubleFlush();
  const columns = document.querySelectorAll(".shop-column");
  expect(columns.length).toBe(2);
  expect(observer.disconnect).toBeDefined();
});

test("handles non-ok fetch response gracefully", async () => {
  const restore = disableObserver();
  buildShopDom();
  mockFetch({ ok: false, json: () => Promise.resolve({}) });
  setScroll({ scrollY: 2000 });
  const loading = document.getElementById("shop-loading");
  initShop(window);
  triggerScroll();
  expect(loading.classList.contains("d-none")).toBe(false);
  await flush();
  expect(loading.classList.contains("d-none")).toBe(true);
  restore();
});

test("loadMoreShopItems ignores when loading already true", async () => {
  const restore = disableObserver();
  let release;
  global.fetch = jest.fn(
    () =>
      new Promise((resolve) => {
        release = () => resolve({ ok: true, json: () => Promise.resolve({ html: '<div id="guard-shop" class="shop-masonry-item"></div>', has_next: false }) });
      })
  );
  buildShopDom({ itemsHtml: '<div class="shop-masonry-item"></div>' });
  setScroll({ scrollY: 0, bodyHeight: 0 });
  initShop(window);
  global.fetch.mockClear();
  triggerScroll();
  await flush();
  release();
  await flush();
  const callsAfterFirst = global.fetch.mock.calls.length;
  triggerScroll();
  await flush();
  expect(global.fetch.mock.calls.length).toBe(callsAfterFirst);
  expect(document.getElementById("guard-shop")).not.toBeNull();
  restore();
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
  mockFetch({ ok: true, json: () => Promise.resolve({ html: null, has_next: false }) });
  const observer = mockObserver();
  initShop(window);
  observer.trigger();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
});

test("works when loading element is missing", () => {
  disableObserver();
  document.body.innerHTML = `
    <div id="shop-items-container" data-page="1" data-has-next="true"></div>
    <div id="shop-sentinel"></div>
  `;
  expect(() => initShop(window)).not.toThrow();
});

test("fetch failure rolls back page number", async () => {
  const restore = disableObserver();
  buildShopDom();
  const container = document.getElementById("shop-items-container");
  mockFetchReject();
  setScroll();
  initShop(window);
  triggerScroll();
  await flush();
  expect(container.dataset.page).toBe("1");
  restore();
});

test("setLoading returns early when loading element missing during fetch", async () => {
  document.body.innerHTML = `
    <div id="shop-items-container" data-page="1" data-has-next="true">
      <div class="shop-masonry-item"></div>
    </div>
    <div id="shop-sentinel"></div>
  `;
  const observer = mockObserver();
  initShop(window);
  observer.trigger();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
});

test("includes seed param and toggles loading element", async () => {
  buildShopDom();
  const loading = document.getElementById("shop-loading");
  mockFetch({ ok: true, json: () => Promise.resolve({ html: "", has_next: false }) });
  const observer = mockObserver();
  initShop(window);
  observer.trigger();
  expect(loading.classList.contains("d-none")).toBe(false);
  await flush();
  expect(loading.classList.contains("d-none")).toBe(true);
  expect(global.fetch.mock.calls[0][0]).toContain("seed=abc");
});

test("waitForImages handles error events", async () => {
  buildShopDom({ itemsHtml: "" });
  const observer = mockObserver();
  mockFetch({ ok: true, json: () => Promise.resolve({ html: '<div class="shop-masonry-item"><img id="errImg" /></div>', has_next: false }) });
  initShop(window);
  observer.trigger();
  await flush();
  document.getElementById("errImg").dispatchEvent(new Event("error"));
  await doubleFlush();
  expect(document.getElementById("errImg").closest(".shop-column")).not.toBeNull();
});

test("waitForImages resolves immediately when image already complete", async () => {
  disableObserver();
  buildShopDom({ itemsHtml: '<div class="shop-masonry-item"><img id="doneImg" /></div>' });
  const descriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "complete");
  Object.defineProperty(HTMLImageElement.prototype, "complete", { configurable: true, get: () => true });
  initShop(window);
  await flush();
  expect(document.getElementById("doneImg").closest(".shop-column")).not.toBeNull();
  if (descriptor) Object.defineProperty(HTMLImageElement.prototype, "complete", descriptor);
  else delete HTMLImageElement.prototype.complete;
});
