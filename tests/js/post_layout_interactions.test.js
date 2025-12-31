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

const renderBackButtonPage = ({ postId = "12", entry, fallback = "/fb" }) => {
  document.body.innerHTML = `
      <div id="post-primary"></div>
      <div class="post-view-similar"></div>
      <a class="post-back-button" data-post-id="${postId}" ${entry ? `data-entry="${entry}"` : ""} data-fallback="${fallback}"></a>
    `;
};

describe("post_layout interactions", () => {
  let originalRAF;
  let originalLocation;
  let originalHistory;
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
    originalHistory = window.history;
    window.history = { length: 0, back: jest.fn(), pushState: jest.fn(), replaceState: jest.fn() };
    originalFormSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = jest.fn();
  });

  afterEach(() => {
    window.requestAnimationFrame = originalRAF;
    global.fetch = realFetch;
    window.location = originalLocation;
    window.history = originalHistory;
    HTMLFormElement.prototype.submit = originalFormSubmit;
    window.sessionStorage.clear();
    jest.clearAllMocks();
  });

  describe("masonry layout", () => {
    test("requestMasonry path when media complete and resize listener", () => {
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

    test("balances columns even when global InfiniteList is present", () => {
      window.InfiniteList = { placeInColumns: jest.fn() };
      document.body.innerHTML = `
        <div class="post-media-masonry">
          <div class="post-media-masonry-item"><img id="tall" /></div>
          <div class="post-media-masonry-item"><img id="short" /></div>
        </div>
        <div class="post-view-similar"></div>
      `;
      mockRect(document.getElementById("tall"), 200);
      mockRect(document.getElementById("short"), 20);
      const { initPostLayout } = loadModule();
      initPostLayout(window);
      const cols = document.querySelectorAll(".post-media-masonry-col");
      expect(cols[0].children.length).toBe(1);
      expect(cols[1].children.length).toBe(1);
      delete window.InfiniteList;
    });

    test("uses one masonry column when only one item on wide screens", () => {
      const originalWidth = window.innerWidth;
      window.innerWidth = 1200;
      document.body.innerHTML = `
        <div class="post-media-masonry">
          <div class="post-media-masonry-item"><img id="solo-img" /></div>
        </div>
        <div class="post-view-similar"></div>
      `;
      const img = document.getElementById("solo-img");
      img.complete = true;
      mockRect(img, 40);
      const { initPostLayout } = loadModule();
      initPostLayout(window);
      const cols = document.querySelectorAll(".post-media-masonry-col");
      expect(cols.length).toBe(2);
      expect(cols[1].style.display).toBe("none");
      window.innerWidth = originalWidth;
    });

    test("rebuilds masonry when media fires error", () => {
      document.body.innerHTML = `
        <div class="post-media-masonry">
          <div class="post-media-masonry-item"><img id="err-img" /></div>
        </div>
        <div class="post-view-similar"></div>
      `;
      const img = document.getElementById("err-img");
      Object.defineProperty(img, "complete", { value: false });
      mockRect(img, 25);
      const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => cb());
      const { initPostLayout } = loadModule();
      initPostLayout(window);
      rafSpy.mockClear();
      img.dispatchEvent(new Event("error"));
      expect(rafSpy).toHaveBeenCalled();
      rafSpy.mockRestore();
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
      expect(cols[1].style.display).toBe("none");
    });

    test("uses setTimeout path and observes masonry when rAF missing", () => {
      const originalTimeout = window.setTimeout;
      window.requestAnimationFrame = undefined;
      window.setTimeout = jest.fn((cb) => cb());
      const observeSpy = jest.fn();
      window.ResizeObserver = jest.fn().mockImplementation((cb) => ({ observe: observeSpy }));
      document.body.innerHTML = `
        <div class="post-media-masonry">
          <div class="post-media-masonry-item"><img id="img-a" /></div>
          <div class="post-media-masonry-item"><img id="img-b" /></div>
        </div>
        <div class="post-view-similar"></div>
      `;
      ["img-a", "img-b"].forEach((id, idx) => {
        const img = document.getElementById(id);
        img.complete = true;
        mockRect(img, idx ? 30 : 60);
      });

      const { initPostLayout } = loadModule();
      initPostLayout(window);

      expect(window.setTimeout).toHaveBeenCalled();
      expect(observeSpy).toHaveBeenCalledWith(document.querySelector(".post-media-masonry"));
      window.setTimeout = originalTimeout;
      delete window.ResizeObserver;
    });
  });

  describe("guards and misc", () => {
    test("handleScroll returns early when primary or similar missing", () => {
      document.body.innerHTML = `<div class="post-view-similar"></div>`;
      const { initPostLayout } = loadModule();
      initPostLayout(window);
      expect(() => window.dispatchEvent(new Event("scroll"))).not.toThrow();
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

    test("sessionStorage errors are handled when resolving back target", () => {
      renderBackButtonPage({ postId: "err", entry: "http://localhost/from" });
      const originalStorage = window.sessionStorage;
      window.sessionStorage = {
        getItem: () => {
        throw new Error("boom");
        },
        setItem: jest.fn(),
        clear: jest.fn()
      };
      const assignSpy = jest.spyOn(window.location, "assign");
      const { initPostLayout } = loadModule();
      expect(() => initPostLayout(window)).not.toThrow();
      expect(() =>
        document.querySelector(".post-back-button").dispatchEvent(new Event("click", { bubbles: true, cancelable: true }))
      ).not.toThrow();
      expect(assignSpy).toHaveBeenCalled();
      window.sessionStorage = originalStorage;
      assignSpy.mockRestore();
    });

    test("back hint visibility runs without rAF and observes gallery", () => {
      window.requestAnimationFrame = undefined;
      const observeSpy = jest.fn();
      window.ResizeObserver = jest.fn().mockImplementation((cb) => ({ observe: observeSpy }));
      document.body.innerHTML = `
        <div id="post-primary"></div>
        <div class="post-view-similar"></div>
        <a class="post-back-button"></a>
        <div class="recipe-gallery"></div>
      `;
      const back = document.querySelector(".post-back-button");
      const gallery = document.querySelector(".recipe-gallery");
      back.getBoundingClientRect = () => ({ top: 10, bottom: 20, right: 5 });
      gallery.getBoundingClientRect = () => ({ top: 15, bottom: 100, left: 40 });

      const { initPostLayout } = loadModule();
      initPostLayout(window);

      expect(back.classList.contains("post-back-button--hide-hint")).toBe(false);
      expect(observeSpy).toHaveBeenCalledWith(gallery);
      delete window.ResizeObserver;
    });

    test("auto init waits for DOMContentLoaded when loading", () => {
      const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
      Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
      const addSpy = jest.spyOn(document, "addEventListener");
      jest.resetModules();
      delete global.__postLayoutInitialized;
      require("../../static/js/post_layout");
      expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
      addSpy.mock.calls[0][1]();
      if (originalReady) {
        Object.defineProperty(document, "readyState", originalReady);
      } else {
        Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
      }
      addSpy.mockRestore();
    });
  });
});
