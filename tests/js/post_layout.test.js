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
});
