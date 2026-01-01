const modulePath = "../../static/js/for_you_infinite";
const { attachGlobal } = require("../../static/js/infinite_list");

const loadModule = () => {
  jest.resetModules();
  delete global.__forYouInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__forYouInfiniteInitialized;
  return mod;
};

let scrollHandlers = [];
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const triggerScroll = () => scrollHandlers.forEach((handler) => handler(new Event("scroll")));
const setScrollDims = ({ bodyHeight = 1000, innerHeight = 1000, scrollY = 1000 } = {}) => {
  window.innerHeight = innerHeight;
  Object.defineProperty(document.body, "offsetHeight", { value: bodyHeight, configurable: true });
  window.scrollY = scrollY;
};

const buildGrid = (hasMore = true, cardCount = 12) => {
  const cards = new Array(cardCount).fill('<div class="my-recipe-card"></div>').join("");
  document.body.innerHTML = `
    <div id="forYou-grid" data-for-you-has-more="${hasMore ? "true" : "false"}">
      <div class="feed-masonry-column">${cards}</div>
      <div class="feed-masonry-column"></div>
    </div>
    <div id="forYou-sentinel"></div>
    <div id="forYou-loading" class="d-none"></div>
  `;
};

let originalFetch;
let addListenerSpy;

beforeEach(() => {
  document.body.innerHTML = "";
  scrollHandlers = [];
  attachGlobal(window);
  addListenerSpy = jest.spyOn(window, "addEventListener").mockImplementation((type, handler) => {
    if (type === "scroll") scrollHandlers.push(handler);
  });
  originalFetch = global.fetch;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="my-recipe-card"></div>', count: 1, has_more: false }) }));
  delete global.__forYouInfiniteInitialized;
});

afterEach(() => {
  global.fetch = originalFetch;
  delete global.IntersectionObserver;
  addListenerSpy.mockRestore();
  jest.clearAllMocks();
});

test("loads more when intersection observer fires", async () => {
  buildGrid(true);
  const observed = [];
  let triggerFn = () => {};
  global.IntersectionObserver = function (cb) {
    this.observe = (el) => observed.push(el);
    triggerFn = (isIntersecting = true) => cb([{ isIntersecting }]);
  };
  loadModule().initForYouInfinite(window);
  expect(observed[0].id).toBe("forYou-sentinel");
  triggerFn();
  await flush();
  expect(document.querySelectorAll(".my-recipe-card").length).toBeGreaterThan(12);
});

test("falls back to scroll listener when no IntersectionObserver", async () => {
  delete global.IntersectionObserver;
  buildGrid(true);
  loadModule().initForYouInfinite(window);
  setScrollDims({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  await flush();
  expect(document.querySelectorAll(".my-recipe-card").length).toBeGreaterThan(12);
});

test("handles fetch errors gracefully and resets loading", async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
  buildGrid(true);
  loadModule().initForYouInfinite(window);
  triggerScroll();
  expect(document.getElementById("forYou-loading").classList.contains("d-none")).toBe(false);
  await flush();
  expect(document.getElementById("forYou-loading").classList.contains("d-none")).toBe(true);
  expect(document.querySelectorAll(".my-recipe-card").length).toBe(12);
});

test("when hasMore already false, no fetch occurs", () => {
  buildGrid(false, 1);
  loadModule().initForYouInfinite(window);
  global.fetch.mockClear();
  triggerScroll();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("handles response without html and stops pagination", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ has_more: false, count: 0 }) }));
  buildGrid(true);
  loadModule().initForYouInfinite(window);
  triggerScroll();
  await flush();
  global.fetch.mockClear();
  triggerScroll();
  await flush();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("distributes new cards to shortest column", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="newCard"></div>', has_more: false, count: 1 }) }));
  buildGrid(true);
  Object.defineProperty(document.querySelectorAll(".feed-masonry-column")[0], "offsetHeight", { value: 100 });
  Object.defineProperty(document.querySelectorAll(".feed-masonry-column")[1], "offsetHeight", { value: 1 });
  loadModule().initForYouInfinite(window);
  triggerScroll();
  await flush();
  expect(document.querySelector(".feed-masonry-column:nth-child(2) #newCard")).not.toBeNull();
});

test("early exits when already initialized, missing window, container, or sentinel", () => {
  const { initForYouInfinite } = loadModule();
  global.__forYouInfiniteInitialized = true;
  expect(() => initForYouInfinite(window)).not.toThrow();
  delete global.__forYouInfiniteInitialized;
  document.body.innerHTML = `<div id="forYou-grid"></div>`;
  expect(() => initForYouInfinite(window)).not.toThrow();
  expect(() => initForYouInfinite(null)).not.toThrow();
});

test("scroll fallback triggers when threshold reached and toggles loading spinner", async () => {
  delete global.IntersectionObserver;
  buildGrid(true);
  loadModule().initForYouInfinite(window);
  setScrollDims({ bodyHeight: 1000, innerHeight: 1000, scrollY: 2000 });
  triggerScroll();
  expect(document.getElementById("forYou-loading").classList.contains("d-none")).toBe(false);
  await flush();
  expect(document.getElementById("forYou-loading").classList.contains("d-none")).toBe(true);
});

test("handles missing loading element gracefully", async () => {
  delete global.IntersectionObserver;
  document.body.innerHTML = `
    <div id="forYou-grid">
      <div class="feed-masonry-column">${new Array(12).fill('<div class="my-recipe-card"></div>').join("")}</div>
    </div>
    <div id="forYou-sentinel"></div>
  `;
  loadModule().initForYouInfinite(window);
  global.fetch.mockClear();
  triggerScroll();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
});
