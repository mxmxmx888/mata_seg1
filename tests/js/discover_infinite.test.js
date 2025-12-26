const modulePath = "../../static/js/discover_infinite";
const { attachGlobal } = require("../../static/js/infinite_list");
let scrollHandlers = [];

function loadModule() {
  jest.resetModules();
  delete global.__discoverInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__discoverInfiniteInitialized;
  return mod;
}

describe("discover_infinite", () => {
  let originalFetch;
  let addEventListenerSpy;

  beforeEach(() => {
    document.body.innerHTML = "";
    scrollHandlers = [];
    attachGlobal(window);
    addEventListenerSpy = jest.spyOn(window, "addEventListener").mockImplementation((type, handler) => {
      if (type === "scroll") {
        scrollHandlers.push(handler);
      }
    });
    originalFetch = global.fetch;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card2"></div>', has_next: false })
      })
    );
  });

  afterEach(() => {
    global.fetch = originalFetch;
    addEventListenerSpy.mockRestore();
    jest.clearAllMocks();
  });

  function setScrollDimensions({ bodyHeight = 1000, innerHeight = 1000, scrollY = 1000 } = {}) {
    window.innerHeight = innerHeight;
    Object.defineProperty(document.body, "offsetHeight", { value: bodyHeight, configurable: true });
    window.scrollY = scrollY;
  }

  function triggerScroll() {
    scrollHandlers.forEach((handler) => handler(new Event("scroll")));
  }

  function loadAndResetModule() {
    const mod = loadModule();
    scrollHandlers = [];
    return mod;
  }

  test("appends new cards on scroll", async () => {
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column" style="height:0">
          <div class="my-recipe-card" id="card1"></div>
        </div>
        <div class="feed-masonry-column" style="height:0"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);

    setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
    triggerScroll();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("card2")).not.toBeNull();
  });

  test("no container early-exits without error", () => {
    document.body.innerHTML = ``;
    const { initDiscoverInfinite } = loadAndResetModule();
    expect(() => initDiscoverInfinite(window)).not.toThrow();
  });

  test("early return when already initialized or window missing", () => {
    const { initDiscoverInfinite } = loadAndResetModule();
    global.__discoverInfiniteInitialized = true;
    expect(() => initDiscoverInfinite(window)).not.toThrow();
    delete global.__discoverInfiniteInitialized;
    expect(() => initDiscoverInfinite(null)).not.toThrow();
  });

  test("onScroll triggers when threshold reached", async () => {
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column" style="height:0"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 1000, configurable: true });
    window.scrollY = 2000;
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalled();
  });

  test("skips fetch when scroll below threshold", () => {
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    setScrollDimensions({ bodyHeight: 2000, innerHeight: 500, scrollY: 500 });
    triggerScroll();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("does not fetch when has_next is false", () => {
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="false">
        <div class="feed-masonry-column" style="height:0"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
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

    const { initDiscoverInfinite } = loadModule();
    initDiscoverInfinite(window);
    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
    window.scrollY = 0;
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(1);
    const firstCount = global.fetch.mock.calls.length;

    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch.mock.calls.length).toBeGreaterThan(firstCount);
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

    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("card2").parentElement.id).toBe("col2");
  });

  test("handles response without html", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ has_next: true })
      })
    );
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(document.querySelector(".my-recipe-card")).toBeNull();
  });

  test("non-ok response resets loading and allows retry", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({})
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card3"></div>', has_next: false })
      });

    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    triggerScroll();
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(document.getElementById("card3")).not.toBeNull();
  });

  test("does not double-fetch while loading true", async () => {
    let release;
    global.fetch = jest
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            release = () =>
              resolve({
                ok: true,
                json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card4"></div>', has_next: false })
              });
          })
      )
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="my-recipe-card" id="card4-extra"></div>', has_next: false })
      });
    document.body.innerHTML = `
      <div id="discover-grid" data-page="1" data-popular-has-next="true">
        <div class="feed-masonry-column"></div>
      </div>
    `;
    const { initDiscoverInfinite } = loadAndResetModule();
    initDiscoverInfinite(window);
    setScrollDimensions({ bodyHeight: 0, innerHeight: 1000, scrollY: 0 });
    triggerScroll();
    triggerScroll();
    expect(global.fetch).toHaveBeenCalledTimes(1);
    release();
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("card4")).not.toBeNull();
  });

  test("no columns exits cleanly", () => {
    document.body.innerHTML = `<div id="discover-grid" data-page="1"></div>`;
    const { initDiscoverInfinite } = loadAndResetModule();
    expect(() => initDiscoverInfinite(window)).not.toThrow();
  });
});
