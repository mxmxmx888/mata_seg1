const modulePath = "../../static/js/navbar_follow";

function loadModule() {
  jest.resetModules();
  delete global.__navbarFollowInitialized;
  const mod = require(modulePath);
  delete global.__navbarFollowInitialized;
  return mod;
}

describe("navbar_follow", () => {
  let originalFetch;
  let originalLocation;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    originalLocation = global.location;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    if (originalLocation) {
      global.location = originalLocation;
    }
    jest.clearAllMocks();
  });

  test("toggles follow state via ajax", async () => {
    document.body.innerHTML = `
      <form class="notification-follow-form" action="/follow">
        <input name="csrfmiddlewaretoken" value="token" />
        <button class="btn btn-primary" data-follow-state="not-following">Follow</button>
      </form>
    `;
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    const form = document.querySelector(".notification-follow-form");
    const btn = form.querySelector("button");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/follow"), expect.objectContaining({
      headers: expect.objectContaining({ "X-CSRFToken": "token" })
    }));
    expect(btn.textContent).toBe("Following");
    expect(btn.classList.contains("btn-outline-light")).toBe(true);
    expect(btn.getAttribute("data-follow-state")).toBe("following");

    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(btn.textContent).toBe("Follow");
    expect(btn.classList.contains("btn-primary")).toBe(true);
    expect(btn.getAttribute("data-follow-state")).toBe("not-following");
  });

  test("falls back to native submit when no button", async () => {
    document.body.innerHTML = `<form class="notification-follow-form" action="/fallback"></form>`;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    const form = document.querySelector("form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("navigates to post when clicking notification item", () => {
    document.body.innerHTML = `
      <div class="notification-item" data-post-url="/posts/1">
        <span class="notification-message">A</span>
      </div>
    `;
    delete global.location;
    global.location = { href: "" };

    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    document.querySelector(".notification-item").dispatchEvent(new Event("click", { bubbles: true }));
    expect(global.location.href).toBe("/posts/1");
  });

  test("ignores click when inside interactive element", () => {
    document.body.innerHTML = `
      <div class="notification-item" data-post-url="/posts/2">
        <a href="/skip">Link</a>
      </div>
    `;
    delete global.location;
    global.location = { href: "" };

    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    const link = document.querySelector("a");
    link.dispatchEvent(new Event("click", { bubbles: true }));
    expect(global.location.href).toBe("");
  });

  test("accept action updates message and removes actions", async () => {
    document.body.innerHTML = `
      <div data-notification-id="1">
        <div class="notification-message">sent request.</div>
        <div class="notification-follow-request-actions"></div>
        <form class="notification-follow-request-form" data-action="accept" action="/accept"></form>
      </div>
    `;
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    const form = document.querySelector(".notification-follow-request-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.querySelector(".notification-message").textContent).toBe("started following you.");
    expect(document.querySelector(".notification-follow-request-actions")).toBeNull();
  });

  test("reject action removes notification item", async () => {
    document.body.innerHTML = `
      <div data-notification-id="2">
        <form class="notification-follow-request-form" data-action="reject" action="/reject"></form>
      </div>
    `;
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);

    const item = document.querySelector("[data-notification-id]");
    item.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector("[data-notification-id]")).toBeNull();
  });

  test("fetch failure falls back to native submit", async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    document.body.innerHTML = `<form class="notification-follow-form" action="/fallback"><button data-follow-state="following"></button></form>`;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("notification click ignored when target inside link", () => {
    document.body.innerHTML = `
      <div class="notification-item" data-post-url="/posts/2">
        <a href="/other"><span class="notification-message">A</span></a>
      </div>
    `;
    delete global.location;
    global.location = { href: "" };
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);
    document.querySelector("a").dispatchEvent(new Event("click", { bubbles: true }));
    expect(global.location.href).toBe("");
  });

  test("exits safely when no follow elements exist", () => {
    document.body.innerHTML = ``;
    const { initNavbarFollow } = loadModule();
    expect(() => initNavbarFollow(window)).not.toThrow();
  });

  test("follow request failure falls back to submit", async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    document.body.innerHTML = `
      <div data-notification-id="3">
        <form class="notification-follow-request-form" data-action="accept" action="/accept"></form>
      </div>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initNavbarFollow } = loadModule();
    initNavbarFollow(window);
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });
});
