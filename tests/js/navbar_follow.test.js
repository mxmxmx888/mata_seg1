const modulePath = "../../static/js/navbar_follow";

const loadModule = () => {
  jest.resetModules();
  delete global.__navbarFollowInitialized;
  const mod = require(modulePath);
  delete global.__navbarFollowInitialized;
  return mod;
};

const render = (html = "") => {
  document.body.innerHTML = html;
};

const init = () => loadModule().initNavbarFollow(window);

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

const setLocation = (href = "") => {
  delete global.location;
  global.location = { href };
};

let originalFetch;
let originalLocation;

beforeEach(() => {
  render();
  originalFetch = global.fetch;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
  originalLocation = global.location;
});

afterEach(() => {
  global.fetch = originalFetch;
  if (originalLocation) global.location = originalLocation;
  jest.clearAllMocks();
});

test("toggles follow state via ajax", async () => {
  render(`
    <form class="notification-follow-form" action="/follow">
      <input name="csrfmiddlewaretoken" value="token" />
      <button class="btn btn-primary" data-follow-state="not-following">Follow</button>
    </form>
  `);
  init();
  const form = document.querySelector(".notification-follow-form");
  const btn = form.querySelector("button");
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(btn.textContent).toBe("Following");
  expect(btn.classList.contains("btn-outline-light")).toBe(true);
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(btn.textContent).toBe("Follow");
  expect(btn.classList.contains("btn-primary")).toBe(true);
});

test("falls back to native submit when no button", async () => {
  render(`<form class="notification-follow-form" action="/fallback"></form>`);
  const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
  init();
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("fetch failure falls back to native submit", async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
  render(`<form class="notification-follow-form" action="/fallback"><button data-follow-state="following"></button></form>`);
  const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
  init();
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("omits csrf header when token absent", async () => {
  render(`
    <form class="notification-follow-form" action="/follow">
      <button data-follow-state="not-following">Follow</button>
    </form>
  `);
  init();
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  const headers = global.fetch.mock.calls[0][1].headers;
  expect(headers["X-CSRFToken"]).toBeUndefined();
});

test("navigates to post when clicking notification item", () => {
  render(`<div class="notification-item" data-post-url="/posts/1"><span>A</span></div>`);
  setLocation("");
  init();
  document.querySelector(".notification-item").dispatchEvent(new Event("click", { bubbles: true }));
  expect(global.location.href).toBe("/posts/1");
});

test("ignores click when inside interactive element or no url", () => {
  render(`
    <div class="notification-item" data-post-url="/posts/2"><a href="/skip">Link</a></div>
    <div class="notification-item"><button>Btn</button></div>
  `);
  setLocation("");
  init();
  document.querySelector("a").dispatchEvent(new Event("click", { bubbles: true }));
  document.querySelectorAll(".notification-item")[1].dispatchEvent(new Event("click", { bubbles: true }));
  expect(global.location.href).toBe("");
});

test("accept action updates message and removes actions", async () => {
  render(`
    <div data-notification-id="1">
      <div class="notification-message">sent request.</div>
      <div class="notification-follow-request-actions"></div>
      <form class="notification-follow-request-form" data-action="accept" action="/accept"></form>
    </div>
  `);
  init();
  const form = document.querySelector(".notification-follow-request-form");
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(document.querySelector(".notification-message").textContent).toBe("started following you.");
  expect(document.querySelector(".notification-follow-request-actions")).toBeNull();
});

test("reject action removes notification item", async () => {
  render(`
    <div data-notification-id="2">
      <form class="notification-follow-request-form" data-action="reject" action="/reject"></form>
    </div>
  `);
  init();
  const item = document.querySelector("[data-notification-id]");
  item.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(document.querySelector("[data-notification-id]")).toBeNull();
});

test("follow request failure falls back to submit", async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
  render(`
    <div data-notification-id="3">
      <form class="notification-follow-request-form" data-action="accept" action="/accept"></form>
    </div>
  `);
  const submitSpy = jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
  init();
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("exits safely when no follow elements exist or already initialized", () => {
  const { initNavbarFollow } = loadModule();
  expect(() => initNavbarFollow(window)).not.toThrow();
  global.__navbarFollowInitialized = true;
  expect(() => initNavbarFollow(window)).not.toThrow();
  delete global.__navbarFollowInitialized;
  expect(() => initNavbarFollow(null)).not.toThrow();
});
