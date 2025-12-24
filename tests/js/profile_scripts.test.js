const path = "../../static/js/profile_scripts";

function loadModule() {
  jest.resetModules();
  delete global.__profileScriptsInitialized;
  const mod = require(path);
  delete global.__profileScriptsInitialized;
  return mod;
}

describe("profile_scripts", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    delete global.bootstrap;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    delete global.bootstrap;
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test("opens modal with bootstrap when available", () => {
    document.body.innerHTML = `
      <button data-bs-target="#followersModal"></button>
      <div id="followersModal"></div>
    `;
    const mockInstance = { show: jest.fn() };
    global.bootstrap = { Modal: { getOrCreateInstance: () => mockInstance } };

    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    document.querySelector("[data-bs-target=\"#followersModal\"]").click();
    expect(mockInstance.show).toHaveBeenCalled();
  });

  test("shows fallback modal and hides on backdrop click without bootstrap", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `
      <button data-bs-target="#closeFriendsModal"></button>
      <div id="closeFriendsModal" aria-hidden="true"></div>
    `;

    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    document.querySelector("[data-bs-target=\"#closeFriendsModal\"]").click();
    jest.runAllTimers();

    const modal = document.getElementById("closeFriendsModal");
    const backdrop = document.querySelector(".custom-modal-backdrop");
    expect(modal.classList.contains("show")).toBe(true);
    expect(backdrop.classList.contains("show")).toBe(true);

    backdrop.click();
    expect(modal.classList.contains("show")).toBe(false);
  });

  test("follow toggle falls back to native submit on error", async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    document.body.innerHTML = `
      <form class="follow-toggle-form" action="/toggle">
        <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
      </form>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("follow toggle form hovers and removes list item after ajax", async () => {
    document.body.innerHTML = `
      <ul>
        <li>
          <form class="follow-toggle-form" action="/toggle">
            <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
          </form>
        </li>
      </ul>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    const btn = document.querySelector(".follow-toggle-btn");
    btn.dispatchEvent(new Event("mouseenter"));
    expect(btn.textContent).toBe("Unfollow");
    btn.dispatchEvent(new Event("mouseleave"));
    expect(btn.textContent).toBe("Following");

    const li = document.querySelector("li");
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).toHaveBeenCalledWith("/toggle", expect.objectContaining({ method: "POST" }));
    expect(li.isConnected).toBe(false);
  });

  test("follow toggle form falls back to native submit on error", async () => {
    document.body.innerHTML = `
      <form class="follow-toggle-form" action="/toggle">
        <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
      </form>
    `;
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    global.fetch.mockRejectedValue(new Error("fail"));

    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("filters close friends list on search input", () => {
    document.body.innerHTML = `
      <input id="closeFriendsSearch" />
      <ul id="closeFriendsList">
        <li class="close-friend-item" data-name="alice"></li>
        <li class="close-friend-item" data-name="bob"></li>
      </ul>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    const input = document.getElementById("closeFriendsSearch");
    input.value = "bob";
    input.dispatchEvent(new Event("input"));

    const items = document.querySelectorAll(".close-friend-item");
    expect(items[0].style.display).toBe("none");
    expect(items[1].style.display).toBe("");
  });

  test("close friends ajax toggles action and button label", async () => {
    document.body.innerHTML = `
      <div id="closeFriendsModal">
        <form action="/friends/add/5/">
          <button>Remove</button>
        </form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    const form = document.querySelector("#closeFriendsModal form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(form.getAttribute("action")).toBe("/friends/remove/5/");
    expect(form.querySelector("button").textContent).toBe("Remove");

    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(form.getAttribute("action")).toBe("/friends/add/5/");
    expect(form.querySelector("button").textContent).toBe("Add");
  });

  test("followers modal ajax removes list item", async () => {
    document.body.innerHTML = `
      <div id="followersModal">
        <ul>
          <li>
            <form action="/followers/remove/"></form>
          </li>
        </ul>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);

    const li = document.querySelector("#followersModal li");
    li.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(li.isConnected).toBe(false);
  });

  test("does nothing when no profile elements present", () => {
    document.body.innerHTML = ``;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("fallback modal closes on backdrop and close button", () => {
    document.body.innerHTML = `
      <button data-bs-target="#followingModal"></button>
      <div id="followingModal">
        <button class="btn-close"></button>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const trigger = document.querySelector("[data-bs-target=\"#followingModal\"]");
    trigger.click();
    const modal = document.getElementById("followingModal");
    const backdrop = document.querySelector(".custom-modal-backdrop");
    expect(modal.classList.contains("show")).toBe(true);
    // click backdrop target equals modal
    modal.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(modal.classList.contains("show")).toBe(false);
    trigger.click();
    modal.querySelector(".btn-close").click();
    expect(modal.classList.contains("show")).toBe(false);
    expect(backdrop.classList.contains("show")).toBe(false);
  });

  test("wireFollowModal exits early when modal missing", () => {
    document.body.innerHTML = `<button data-bs-target="#missing"></button>`;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("wireFollowModal with no buttons does nothing", () => {
    document.body.innerHTML = `<div id="followersModal"></div>`;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("fallback backdrop reused across modal opens", () => {
    jest.useFakeTimers();
    document.body.innerHTML = `
      <button data-bs-target="#followersModal"></button>
      <button data-bs-target="#followersModal"></button>
      <div id="followersModal" aria-hidden="true"><button class="btn-close"></button></div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const buttons = document.querySelectorAll("[data-bs-target=\"#followersModal\"]");
    buttons[0].click();
    jest.runAllTimers();
    const backdrop1 = document.querySelector(".custom-modal-backdrop");
    document.querySelector(".btn-close").click();
    buttons[1].click();
    jest.runAllTimers();
    const backdrop2 = document.querySelector(".custom-modal-backdrop");
    expect(backdrop2).toBe(backdrop1);
    jest.useRealTimers();
  });

  test("close friends search filters items", () => {
    document.body.innerHTML = `
      <input id="closeFriendsSearch" />
      <div id="closeFriendsList">
        <div class="close-friend-item" data-name="alice"></div>
        <div class="close-friend-item" data-name="bob"></div>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const input = document.getElementById("closeFriendsSearch");
    input.value = "bob";
    input.dispatchEvent(new Event("input"));
    const items = document.querySelectorAll(".close-friend-item");
    expect(items[0].style.display).toBe("none");
    expect(items[1].style.display).toBe("");
  });

  test("ajax modal forms submit fallback on error", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    document.body.innerHTML = `
      <div id="followersModal">
        <form action="/bad"><button>Go</button></form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("ajax modal forms with ok response and payload skips fallback", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    document.body.innerHTML = `
      <div id="followersModal">
        <form action="/ok"><button>Go</button></form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(submitSpy).not.toHaveBeenCalled();
    submitSpy.mockRestore();
  });

  test("follow toggle form without action exits early", () => {
    document.body.innerHTML = `
      <form class="follow-toggle-form">
        <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
      </form>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    expect(() => document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
  });

  test("follow toggle with missing button is skipped", () => {
    document.body.innerHTML = `<form class="follow-toggle-form" action="/toggle"></form>`;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("json parse failure still triggers ajax success handler with empty payload", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.reject(new Error("bad")) }));
    document.body.innerHTML = `
      <div id="closeFriendsModal">
        <form action="/friends/add/5/">
          <button>Remove</button>
        </form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const form = document.querySelector("#closeFriendsModal form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(form.getAttribute("action")).toBe("/friends/remove/5/");
  });

  test("following modal ajax removes list item", async () => {
    document.body.innerHTML = `
      <div id="followingModal">
        <ul>
          <li>
            <form action="/following/remove/"></form>
          </li>
        </ul>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const li = document.querySelector("#followingModal li");
    li.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(li.isConnected).toBe(false);
  });

  test("attachAjaxModalForms does nothing when form already bound", () => {
    document.body.innerHTML = `
      <div id="followersModal">
        <form action="/ok" data-ajax-bound="1"></form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("returns early when window missing and when already initialized", () => {
    const { initProfileScripts } = loadModule();
    global.__profileScriptsInitialized = true;
    expect(() => initProfileScripts(window)).not.toThrow();
    delete global.__profileScriptsInitialized;
    expect(() => initProfileScripts(null)).not.toThrow();
  });

  test("search input missing list is ignored", () => {
    document.body.innerHTML = `
      <input id="closeFriendsSearch" />
    `;
    const { initProfileScripts } = loadModule();
    expect(() => initProfileScripts(window)).not.toThrow();
  });

  test("ajax modal forms skip when no action or url", () => {
    document.body.innerHTML = `
      <div id="followersModal">
        <form><button>Go</button></form>
      </div>
    `;
    const { initProfileScripts } = loadModule();
    initProfileScripts(window);
    const form = document.querySelector("form");
    expect(() => form.dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
  });
});
