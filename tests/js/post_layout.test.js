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
  let originalFormSubmit;
  const realFetch = global.fetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    delete window.__postLayoutInitialized;
    originalRAF = window.requestAnimationFrame;
    window.requestAnimationFrame = (cb) => cb();
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    originalLocation = window.location;
    delete window.location;
    window.location = { href: "http://localhost/post/1", origin: "http://localhost", assign: jest.fn(), replace: jest.fn() };
    originalFormSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = jest.fn();
  });

  afterEach(() => {
    window.requestAnimationFrame = originalRAF;
    global.fetch = realFetch;
    window.location = originalLocation;
    HTMLFormElement.prototype.submit = originalFormSubmit;
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

    const event = new KeyboardEvent("keydown", { key: "Escape" });
    document.dispatchEvent(event);
    expect(window.location.assign).toHaveBeenCalledWith("/fallback");
  });

  test("escape key handles legacy key values", () => {
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Esc" }));
    expect(window.location.assign).toHaveBeenCalledWith("/fallback");

    window.location.assign.mockClear();
    const keyCodeEvent = new KeyboardEvent("keydown", {});
    Object.defineProperty(keyCodeEvent, "keyCode", { value: 27 });
    document.dispatchEvent(keyCodeEvent);
    expect(window.location.assign).toHaveBeenCalledWith("/fallback");
  });

  test("escape key triggers only on keydown even if keyup follows", () => {
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    document.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape" }));
    expect(window.location.assign).toHaveBeenCalled();
  });

  test("escape key still triggers when event is already handled", () => {
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);

    const preventedEvent = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
    preventedEvent.preventDefault();
    document.dispatchEvent(preventedEvent);
    expect(window.location.assign).toHaveBeenCalledWith("/fallback");
  });

  test("escape still triggers when modal is open", () => {
    document.body.innerHTML = `
      <div class="modal show"></div>
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const assignSpy = jest.spyOn(window.location, "assign");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const event = new KeyboardEvent("keydown", { key: "Escape" });
    document.dispatchEvent(event);
    expect(assignSpy).toHaveBeenCalledWith("/fallback");
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
        <button data-like-toggle data-liked="false"><i class="bi-heart"></i></button>
      </form>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    expect(() => {
      document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    }).not.toThrow();
  });

  test("like form handles non-ok response by submitting", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input type="hidden" name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false" data-count="1"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("handleScroll sets fade amount", () => {
    document.body.innerHTML = `
      <div id="post-primary" class="post-primary">
        <div class="post-primary-img"><img /></div>
      </div>
      <div class="post-view-similar"></div>
    `;
    const { initPostLayout } = loadModule();
    window.scrollY = 10;
    const primary = document.querySelector(".post-primary");
    const setPropertySpy = jest.spyOn(primary.style, "setProperty");
    initPostLayout(window);
    window.dispatchEvent(new Event("scroll"));
    expect(setPropertySpy).toHaveBeenCalledWith("--post-fade-amount", expect.any(String));
    setPropertySpy.mockRestore();
  });

  test("back button uses referrer when same origin", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/from", configurable: true });
    document.body.innerHTML = `
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }));
    expect(window.location.assign).toHaveBeenCalledWith("http://localhost/from");
  });

  test("like form toggles state on fetch success", async () => {
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input type="hidden" name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false" data-count="1"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const btn = document.querySelector("[data-like-toggle]");
    document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    const countEl = document.querySelector("[data-like-count]");
    expect(btn.dataset.liked).toBe("true");
    expect(countEl.textContent).toBe("2");
  });

  test("like form falls back to native submit on error", async () => {
    document.body.innerHTML = `
      <form data-like-form action="/like">
        <input type="hidden" name="csrfmiddlewaretoken" value="token" />
        <button data-like-toggle data-liked="false" data-count="1"><i class="bi-heart"></i></button>
        <span data-like-count>1</span>
      </form>
    `;
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    document.querySelector("[data-like-form]").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("cameFromCreate popstate redirects to fallback", () => {
    Object.defineProperty(document, "referrer", { value: "http://localhost/recipes/create", configurable: true });
    document.body.innerHTML = `
      <a class="post-back-button" data-entry="http://localhost/from" data-fallback="/fallback"></a>
    `;
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const popEvent = new PopStateEvent("popstate", { state: { cameFromCreate: true } });
    window.dispatchEvent(popEvent);
    expect(window.location.replace).toHaveBeenCalledWith("/fallback");
  });

  test("escape key still triggers when lightbox open", () => {
    document.body.innerHTML = `
      <div class="pswp--open"></div>
      <div id="lightbox" class=""></div>
      <a class="post-back-button" data-fallback="/fallback"></a>
    `;
    const assignSpy = jest.spyOn(window.location, "assign");
    const { initPostLayout } = loadModule();
    initPostLayout(window);
    const event = new KeyboardEvent("keydown", { key: "Escape" });
    document.dispatchEvent(event);
    expect(assignSpy).toHaveBeenCalledWith("/fallback");
    assignSpy.mockRestore();
  });
});
