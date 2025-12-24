const modulePath = "../../static/js/for_you_infinite";

function loadModule() {
  jest.resetModules();
  delete global.__forYouInfiniteInitialized;
  const mod = require(modulePath);
  delete global.__forYouInfiniteInitialized;
  return mod;
}

describe("for_you_infinite", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ html: '<div class="my-recipe-card"></div>', count: 1, has_more: false })
      })
    );
    delete global.__forYouInfiniteInitialized;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
    delete global.IntersectionObserver;
  });

  test("loads more when intersection observer fires", async () => {
    const cards = Array.from({ length: 12 }).map(() => '<div class="my-recipe-card"></div>').join("");
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column">${cards}</div>
        <div class="feed-masonry-column"></div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;

    const observed = [];
    let observerInstance = null;
    const MockObserver = function (cb) {
      observerInstance = { trigger: (isIntersecting = true) => cb([{ isIntersecting }]) };
      this.observe = (el) => observed.push(el);
      this.trigger = observerInstance.trigger;
    };
    global.IntersectionObserver = MockObserver;

    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);

    expect(observed[0].id).toBe("forYou-sentinel");
    observerInstance.trigger();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelectorAll(".my-recipe-card").length).toBeGreaterThan(1);
  });

  test("falls back to scroll listener when no IntersectionObserver", async () => {
    delete global.IntersectionObserver;
    const cards = Array.from({ length: 12 }).map(() => '<div class="my-recipe-card"></div>').join("");
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column">${cards}</div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;
    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);

    window.innerHeight = 1000;
    Object.defineProperty(document.body, "offsetHeight", { value: 0, configurable: true });
    window.scrollY = 0;
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelectorAll(".my-recipe-card").length).toBeGreaterThan(1);
  });

  test("handles fetch errors gracefully", async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column"><div class="my-recipe-card"></div></div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;
    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);
    // trigger
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelectorAll(".my-recipe-card").length).toBe(1);
  });

  test("when hasMore already false, no fetch occurs", () => {
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column"><div class="my-recipe-card"></div></div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;
    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);
    // mimic LIMIT offset unmet
    window.dispatchEvent(new Event("scroll"));
    expect(global.fetch).toHaveBeenCalledTimes(0);
  });

  test("handles response without html and stops pagination", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ has_more: false, count: 0 })
      })
    );
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column">
          ${new Array(12).fill('<div class="my-recipe-card"></div>').join("")}
        </div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;
    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    // after has_more false, further scrolls should not refetch
    global.fetch.mockClear();
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).toHaveBeenCalledTimes(0);
  });

  test("distributes new cards to shortest column", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            html: '<div class="my-recipe-card" id="newCard"></div>',
            has_more: false,
            count: 1
          })
      })
    );
    const cards = new Array(12).fill('<div class="my-recipe-card"></div>').join("");
    document.body.innerHTML = `
      <div id="forYou-grid">
        <div class="feed-masonry-column" id="c1">${cards}</div>
        <div class="feed-masonry-column" id="c2">${cards}</div>
      </div>
      <div id="forYou-sentinel"></div>
      <div id="forYou-loading" class="d-none"></div>
    `;
    Object.defineProperty(document.getElementById("c1"), "offsetHeight", { value: 100 });
    Object.defineProperty(document.getElementById("c2"), "offsetHeight", { value: 1 });
    const { initForYouInfinite } = loadModule();
    initForYouInfinite(window);
    window.dispatchEvent(new Event("scroll"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector("#c2 #newCard")).not.toBeNull();
  });
});
