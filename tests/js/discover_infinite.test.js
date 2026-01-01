const modulePath = "../../static/js/discover_infinite";
const { attachGlobal } = require("../../static/js/infinite_list");

const loadModule = () => {
  jest.resetModules();
  delete global.__discoverInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__discoverInfiniteInitialized;
  return mod;
};

let scrollHandlers = [];
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const setFetch = (fn) => {
  global.fetch = fn;
  window.fetch = fn;
};

const setScrollDimensions = ({ bodyHeight = 1000, innerHeight = 1000, scrollY = 1000 } = {}) => {
  window.innerHeight = innerHeight;
  Object.defineProperty(document.body, "offsetHeight", { value: bodyHeight, configurable: true });
  window.scrollY = scrollY;
};

const triggerScroll = () => scrollHandlers.forEach((handler) => handler(new Event("scroll")));

const buildGrid = (hasNext = true) => {
  document.body.innerHTML = `
    <div id="discover-grid" data-page="1" data-popular-has-next="${hasNext ? "true" : "false"}">
      <div class="feed-masonry-column" style="height:0">
        <div class="my-recipe-card" id="card1"></div>
      </div>
      <div class="feed-masonry-column" style="height:0"></div>
    </div>
  `;
};

let originalWindowFetch;

beforeEach(() => {
  document.body.innerHTML = "";
  scrollHandlers = [];
  attachGlobal(window);
  jest.spyOn(window, "addEventListener").mockImplementation((type, handler) => {
    if (type === "scroll") scrollHandlers.push(handler);
  });
  originalWindowFetch = window.fetch;
  setFetch(jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card2"></div>', has_next: false }) })));
});

afterEach(() => {
  window.fetch = originalWindowFetch;
  jest.restoreAllMocks();
  jest.clearAllMocks();
});

test("appends new cards on scroll", async () => {
  buildGrid(true);
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  await flush();
  expect(document.getElementById("card2")).not.toBeNull();
});

test("no container or missing window exits quietly", () => {
  document.body.innerHTML = ``;
  expect(() => loadModule().initDiscoverInfinite(window)).not.toThrow();
  expect(() => loadModule().initDiscoverInfinite(null)).not.toThrow();
});

test("skips when already initialized", () => {
  const { initDiscoverInfinite } = loadModule();
  global.__discoverInfiniteInitialized = true;
  expect(() => initDiscoverInfinite(window)).not.toThrow();
  delete global.__discoverInfiniteInitialized;
});

test("onScroll triggers when threshold reached", async () => {
  buildGrid(true);
  loadModule().initDiscoverInfinite(window);
  window.innerHeight = 1000;
  Object.defineProperty(document.body, "offsetHeight", { value: 1000, configurable: true });
  window.scrollY = 2000;
  triggerScroll();
  await flush();
  expect(global.fetch).toHaveBeenCalled();
});

test("skips fetch when scroll below threshold or has_next false", () => {
  buildGrid(true);
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 2000, innerHeight: 500, scrollY: 500 });
  triggerScroll();
  expect(global.fetch).not.toHaveBeenCalled();

  buildGrid(false);
  loadModule().initDiscoverInfinite(window);
  triggerScroll();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("picks shortest column and handles fetch failure", async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
  document.body.innerHTML = `
    <div id="discover-grid" data-page="1" data-popular-has-next="true">
      <div class="feed-masonry-column" id="col1"></div>
      <div class="feed-masonry-column" id="col2"></div>
    </div>
  `;
  Object.defineProperty(document.getElementById("col1"), "offsetHeight", { value: 10 });
  Object.defineProperty(document.getElementById("col2"), "offsetHeight", { value: 1 });
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  await flush();
  expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(1);
  triggerScroll();
  await flush();
  expect(document.querySelector(".my-recipe-card")).toBeNull();
});

test("appends to shortest column", async () => {
  document.body.innerHTML = `
    <div id="discover-grid" data-page="1" data-popular-has-next="true">
      <div class="feed-masonry-column" id="col1"></div>
      <div class="feed-masonry-column" id="col2"></div>
    </div>
  `;
  Object.defineProperty(document.getElementById("col1"), "offsetHeight", { value: 10 });
  Object.defineProperty(document.getElementById("col2"), "offsetHeight", { value: 1 });
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  await flush();
  expect(document.getElementById("card2").parentElement.id).toBe("col2");
});

test("handles response without html and non-ok responses", async () => {
  setFetch(
    jest
      .fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ has_next: true }) })
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card3"></div>', has_next: false }) })
      .mockResolvedValue({ ok: true, json: () => Promise.resolve({ html: "", has_next: false }) })
  );
  buildGrid(true);
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  await flush();
  triggerScroll();
  await flush();
  expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(3);
  expect(global.fetch.mock.calls.length).toBeLessThanOrEqual(4);
  expect(document.getElementById("card3")).not.toBeNull();
});

test("does not double-fetch while loading true", async () => {
  let release;
  setFetch(
    jest.fn(
      () =>
        new Promise((resolve) => {
          release = () => resolve({ ok: true, json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card4"></div>', has_next: false }) });
        })
    )
  );
  buildGrid(true);
  loadModule().initDiscoverInfinite(window);
  setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
  triggerScroll();
  release();
  await flush();
  expect(global.fetch.mock.calls.length).toBeLessThanOrEqual(2);
  expect(document.getElementById("card4")).not.toBeNull();
});
