const modulePath = "../../static/js/post_layout";

function loadModule() {
  jest.resetModules();
  delete global.__postLayoutInitialized;
  const mod = require(modulePath);
  delete global.__postLayoutInitialized;
  return mod;
}

function mockRect(el, height) {
  el.getBoundingClientRect = () => ({ height });
}

describe("post_layout", () => {
  let originalRAF;
  let originalLocation;
  const realFetch = global.fetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalRAF = window.requestAnimationFrame;
    window.requestAnimationFrame = (cb) => cb();
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    originalLocation = window.location;
    delete window.location;
    window.location = { href: "http://localhost/post/1", origin: "http://localhost", assign: jest.fn(), replace: jest.fn() };
  });

  afterEach(() => {
    window.requestAnimationFrame = originalRAF;
    global.fetch = realFetch;
    window.location = originalLocation;
    jest.clearAllMocks();
  });

  test("builds masonry columns and distributes items", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img /></div>
        <div class="post-media-masonry-item" id="item2"><img /></div>
      </div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const items = masonry.querySelectorAll(".post-media-masonry-item");
    items.forEach((item, idx) => {
      const img = item.querySelector("img");
      img.complete = true;
      mockRect(img, idx === 0 ? 100 : 10);
    });

    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const cols = masonry.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBe(2);
    expect(cols[0].children.length + cols[1].children.length).toBe(2);
  });

  test("sets similar grid column CSS variable based on width", () => {
    const grid = document.createElement("div");
    grid.className = "view-similar-grid";
    Object.defineProperty(grid, "clientWidth", { value: 300 });
    document.body.appendChild(grid);

    const { initPostLayout } = loadModule();
    initPostLayout(window);

    expect(grid.style.getPropertyValue("--similar-cols")).not.toBe("");
  });

  test("escape key triggers back when no modal or lightbox", () => {
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const event = new KeyboardEvent("keyup", { key: "Escape" });
    document.dispatchEvent(event);
    expect(window.location.assign).toHaveBeenCalledWith("/fallback");
  });

  test("escape does nothing when modal is open", () => {
    document.body.innerHTML = `
      <div class="modal show"></div>
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const assignSpy = jest.spyOn(window.location, "assign");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const event = new KeyboardEvent("keyup", { key: "Escape" });
    document.dispatchEvent(event);
    expect(assignSpy).not.toHaveBeenCalled();
    assignSpy.mockRestore();
  });

  test("like form with missing csrf does nothing special", async () => {
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <button data-like-toggle data-liked="false"><i class="bi-heart"></i></button>
      </form>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    expect(() => {
      document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    }).not.toThrow();
  });

  test("back button assigns referrer when history not available", () => {
    window.history.length = 1;
    Object.defineProperty(document, "referrer", { value: "http://localhost/from", configurable: true });
    document.body.innerHTML = `
      <a class="post-back-button" data-entry="http://localhost/from" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(window.location.assign).toHaveBeenCalledWith("http://localhost/from");
  });

  test("like form returns early when fetch undefined", () => {
    delete global.fetch;
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    expect(() => {
      document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    }).not.toThrow();
    expect(submitSpy).not.toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("like form handles non-ok response by submitting", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("handleScroll sets fade amount", () => {
    document.body.innerHTML = `
      <div id="post-primary" style="--post-fade-amount:0"></div>
      <div class="post-view-similar" style="height:100px"></div>
    `;
    const primary = document.getElementById("post-primary");
    const similar = document.querySelector(".post-view-similar");
    similar.getBoundingClientRect = () => ({ top: 100 });
    window.innerHeight = 200;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    window.dispatchEvent(new Event("scroll"));
    expect(primary.style.getPropertyValue("--post-fade-amount")).not.toBe("");
  });

  test("back button uses referrer when same origin", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/from", configurable: true });
    document.body.innerHTML = `
      <a class="post-back-button" data-entry="http://localhost/from" data-fallback="/home"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(window.location.assign).toHaveBeenCalledWith("http://localhost/from");
  });

  test("like form toggles state on fetch success", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const form = document.querySelector("[data-like-form]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    const icon = document.querySelector("i");
    expect(icon.classList.contains("bi-heart-fill")).toBe(true);
  });

  test("like form falls back to native submit on error", async () => {
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="true"><i class="bi-heart-fill"></i></button>
        <span data-like-count>2</span>
      </form>
    `;
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const form = document.querySelector("[data-like-form]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("cameFromCreate popstate redirects to fallback", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/recipes/create/", configurable: true });
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
      <div class="post-view-similar"></div>
    `;
    const replaceSpy = jest.spyOn(window.location, "replace").mockImplementation(() => {});
    const pushSpy = jest.spyOn(window.history, "pushState");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(pushSpy).toHaveBeenCalled();
    expect(replaceSpy).toHaveBeenCalledWith("/fallback");
    replaceSpy.mockRestore();
    pushSpy.mockRestore();
  });

  test("escape key ignored when lightbox open", () => {
    document.body.innerHTML = `
      <div class="modal show"></div>
      <div class="post-view-similar"></div>
      <div id="lightbox" class="">Open</div>
      <a class="post-back-button" data-fallback="/fb"></a>
    `;
    const assignSpy = jest.spyOn(window.location, "assign");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape" }));
    expect(assignSpy).not.toHaveBeenCalled();
    assignSpy.mockRestore();
  });

  test("history back path when history length > 1", () => {
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-fallback="/fb"></a>
    `;
    window.history.length = 2;
    const backSpy = jest.spyOn(window.history, "back").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape" }));
    expect(backSpy).toHaveBeenCalled();
    backSpy.mockRestore();
  });

  test("parseUrl returns null for invalid ref and backButton absent", () => {
    Object.defineProperty(document, "referrer", { value: "::::", configurable: true });
    document.body.innerHTML = `
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("masonry requestMasonry path when media complete and resize listener", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = masonry.querySelector("img");
    img.complete = true;
    mockRect(img, 40);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    window.dispatchEvent(new Event("resize"));
    const cols = masonry.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("media load listener requests masonry when not complete", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img id="img1" /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = document.getElementById("img1");
    Object.defineProperty(img, "complete", { value: false });
    mockRect(img, 30);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    img.dispatchEvent(new Event("load"));
    expect(masonry.querySelectorAll(".post-media-masonry-col").length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("back button click uses history when available", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/ref", configurable: true });
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://localhost/ref"></a>
    `;
    window.history.length = 3;
    const backSpy = jest.spyOn(window.history, "back").mockImplementation(() => {});
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    btn.dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(backSpy).toHaveBeenCalled();
    backSpy.mockRestore();
  });

  test("parseUrl catch path handles invalid URL", () => {
    Object.defineProperty(document, "referrer", { value: "::::", configurable: true });
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("resolveBackTarget handles invalid data-entry and fallback href", () => {
    Object.defineProperty(document, "referrer", { value: "" , configurable: true });
    document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://[" href="/from-attr"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    expect(btn.getAttribute("href")).toBe("/from-attr");
  });
  test("handles media load events to rebuild masonry", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><img /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const masonry = document.querySelector(".post-media-masonry");
    const img = masonry.querySelector("img");
    img.complete = false;
    mockRect(img, 50);
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    img.dispatchEvent(new Event("load"));
    const cols = masonry.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBeGreaterThan(0);
    rafSpy.mockRestore();
  });

  test("gracefully exits when no masonry or similar grids", () => {
    document.body.innerHTML = `
      <div id="post-primary"></div>
    `;
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout(window)).not.toThrow();
  });

  test("handles narrow viewport with single masonry column and no media rect", () => {
    document.body.innerHTML = `
      <div class="post-media-masonry">
        <div class="post-media-masonry-item" id="item1"><div class="inner"></div></div>
        <div class="post-media-masonry-item" id="item2"><div class="inner"></div></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    window.innerWidth = 500;
    const items = document.querySelectorAll(".post-media-masonry-item");
    items.forEach((item) => {
      item.getBoundingClientRect = () => ({ height: 5 });
    });
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const cols = document.querySelectorAll(".post-media-masonry-col");
    expect(cols.length).toBe(2);
    // only first column visible
    expect(cols[1].style.display).toBe("none");
  });

  test("handleScroll returns early when primary or similar missing", () => {
    document.body.innerHTML = `<div class="post-view-similar"></div>`;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    expect(() => window.dispatchEvent(new Event("scroll"))).not.toThrow();
  });

  test("resolveBackTarget uses fallback when referrer different origin", () => {
    Object.defineProperty(document, "referrer", { value: "http://other/from", configurable: true });
    document.body.innerHTML = `
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-entry="http://other/from" data-fallback="/fb"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector(".post-back-button");
    expect(btn.getAttribute("href")).toBe("/fb");
  });

  test("like form parseCount handles NaN and clamps count", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="true"><i class="bi-heart-fill"></i></button>
        <span data-like-count>not-a-number</span>
      </form>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const form = document.querySelector("[data-like-form]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.querySelector("[data-like-count]").textContent).toBe("0");
  });

  test("early return when window lacks document", () => {
    const { initPostLayout } = loadModule();
    expect(() => initPostLayout({})).not.toThrow();
  });
});
