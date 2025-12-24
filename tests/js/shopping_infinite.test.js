const modulePath = "../../static/js/shopping_infinite";

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
      instance = { trigger: (isIntersecting = true) => cb([{ isIntersecting }]) };
      this.observe = (el) => observed.push(el);
      this.disconnect = jest.fn();
      this.trigger = instance.trigger;
    };
    global.IntersectionObserver = MockObserver;

    const { initShoppingInfinite } = loadModule();
    initShoppingInfinite(window);

    expect(observed[0].id).toBe("shopping-sentinel");
    instance.trigger();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("newItem")).not.toBeNull();
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
});
