const path = "../../static/js/profile_scripts";

function loadModule() {
  jest.resetModules();
  delete global.__profileScriptsInitialized;
  const mod = require(path);
  delete global.__profileScriptsInitialized;
  return mod;
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const render = (html = "") => {
  document.body.innerHTML = html;
};
const init = () => loadModule().initProfileScripts(window);
const submitAndFlush = async (form) => {
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await flush();
};
const spyOnNativeSubmit = () => jest.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
const mockFetchResolve = (payload = {}, ok = true) => {
  global.fetch = jest.fn(() => Promise.resolve({ ok, json: () => Promise.resolve(payload) }));
};
const mockFetchReject = () => {
  global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
};

let originalFetch;

beforeEach(() => {
  document.body.innerHTML = "";
  originalFetch = global.fetch;
  mockFetchResolve({});
  delete global.bootstrap;
  delete global.InfiniteList;
});

afterEach(() => {
  global.fetch = originalFetch;
  delete global.bootstrap;
  delete global.InfiniteList;
  jest.useRealTimers();
  jest.clearAllMocks();
});

test("follow toggle hovers labels and removes list item after ajax", async () => {
  render(`
    <ul>
      <li>
        <form class="follow-toggle-form" action="/toggle">
          <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
        </form>
      </li>
    </ul>
  `);
  init();
  const btn = document.querySelector(".follow-toggle-btn");
  btn.dispatchEvent(new Event("mouseenter"));
  expect(btn.textContent).toBe("Unfollow");
  btn.dispatchEvent(new Event("mouseleave"));
  expect(btn.textContent).toBe("Following");
  const li = document.querySelector("li");
  await submitAndFlush(document.querySelector("form"));
  expect(global.fetch).toHaveBeenCalledWith("/toggle", expect.objectContaining({ method: "POST" }));
  expect(li.isConnected).toBe(false);
});

test("follow toggle falls back to native submit on fetch reject", async () => {
  mockFetchReject();
  render(`
    <form class="follow-toggle-form" action="/toggle">
      <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
    </form>
  `);
  const submitSpy = spyOnNativeSubmit();
  init();
  await submitAndFlush(document.querySelector("form"));
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("follow toggle falls back when response is not ok", async () => {
  mockFetchResolve({}, false);
  render(`
    <form class="follow-toggle-form" action="/toggle">
      <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
    </form>
  `);
  const submitSpy = spyOnNativeSubmit();
  init();
  await submitAndFlush(document.querySelector("form"));
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("follow toggle without action exits early", () => {
  render(`
    <form class="follow-toggle-form">
      <button class="follow-toggle-btn" data-label-following="Following" data-label-unfollow="Unfollow">Following</button>
    </form>
  `);
  init();
  expect(() => document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
});

test("follow toggle with missing button is skipped", () => {
  render(`<form class="follow-toggle-form" action="/toggle"></form>`);
  init();
  expect(() => document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
});

test("filters close friends list on search input", () => {
  render(`
    <input id="closeFriendsSearch" />
    <ul id="closeFriendsList">
      <li class="close-friend-item" data-name="alice"></li>
      <li class="close-friend-item" data-name="bob"></li>
    </ul>
  `);
  init();
  const input = document.getElementById("closeFriendsSearch");
  input.value = "bob";
  input.dispatchEvent(new Event("input"));
  const items = document.querySelectorAll(".close-friend-item");
  expect(items[0].style.display).toBe("none");
  expect(items[1].style.display).toBe("");
});

test("close friends ajax toggles action and button label", async () => {
  render(`
    <div id="closeFriendsModal">
      <form action="/friends/add/5/">
        <button>Remove</button>
      </form>
    </div>
  `);
  init();
  const form = document.querySelector("#closeFriendsModal form");
  await submitAndFlush(form);
  expect(form.getAttribute("action")).toBe("/friends/remove/5/");
  expect(form.querySelector("button").textContent).toBe("Remove");
  await submitAndFlush(form);
  expect(form.getAttribute("action")).toBe("/friends/add/5/");
  expect(form.querySelector("button").textContent).toBe("Add");
});

test("json parse failure still toggles close friends action", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.reject(new Error("bad")) }));
  render(`
    <div id="closeFriendsModal">
      <form action="/friends/add/5/">
        <button>Remove</button>
      </form>
    </div>
  `);
  init();
  const form = document.querySelector("#closeFriendsModal form");
  await submitAndFlush(form);
  expect(form.getAttribute("action")).toBe("/friends/remove/5/");
});

test("followers modal ajax removes list item", async () => {
  render(`
    <div id="followersModal">
      <ul>
        <li>
          <form action="/followers/remove/"></form>
        </li>
      </ul>
    </div>
  `);
  init();
  const li = document.querySelector("#followersModal li");
  await submitAndFlush(li.querySelector("form"));
  expect(li.isConnected).toBe(false);
});

test("following modal ajax removes list item", async () => {
  render(`
    <div id="followingModal">
      <ul>
        <li>
          <form action="/following/remove/"></form>
        </li>
      </ul>
    </div>
  `);
  init();
  const li = document.querySelector("#followingModal li");
  await submitAndFlush(li.querySelector("form"));
  expect(li.isConnected).toBe(false);
});

test("ajax modal forms fall back when fetch response not ok", async () => {
  mockFetchResolve({}, false);
  const submitSpy = spyOnNativeSubmit();
  render(`
    <div id="followersModal">
      <form action="/bad"><button>Go</button></form>
    </div>
  `);
  init();
  await submitAndFlush(document.querySelector("form"));
  expect(submitSpy).toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("ajax modal forms skip fallback when ok response", async () => {
  mockFetchResolve({});
  const submitSpy = spyOnNativeSubmit();
  render(`
    <div id="followersModal">
      <form action="/ok"><button>Go</button></form>
    </div>
  `);
  init();
  await submitAndFlush(document.querySelector("form"));
  expect(submitSpy).not.toHaveBeenCalled();
  submitSpy.mockRestore();
});

test("ajax modal forms skip when no action or url", () => {
  render(`
    <div id="followersModal">
      <form><button>Go</button></form>
    </div>
  `);
  init();
  const form = document.querySelector("form");
  expect(() => form.dispatchEvent(new Event("submit", { cancelable: true }))).not.toThrow();
});

test("does nothing when no profile elements present", () => {
  render();
  expect(() => init()).not.toThrow();
});

test("returns early when window missing and when already initialized", () => {
  const { initProfileScripts } = loadModule();
  global.__profileScriptsInitialized = true;
  expect(() => initProfileScripts(window)).not.toThrow();
  delete global.__profileScriptsInitialized;
  expect(() => initProfileScripts(null)).not.toThrow();
});

test("search input without list is ignored", () => {
  render(`<input id="closeFriendsSearch" />`);
  expect(() => init()).not.toThrow();
});
