const { setInitialTheme, initBaseInteractions } = require("../../static/js/base_theme_nav");

const render = (html = "") => {
  document.body.innerHTML = html;
};

const init = () => initBaseInteractions(window);

const setMatchMedia = (matches = false, listeners = []) => {
  const mock = {
    matches,
    addEventListener: (event, cb) => listeners.push(cb),
    removeEventListener: jest.fn()
  };
  window.matchMedia = jest.fn().mockReturnValue(mock);
  return { mock, listeners };
};

const triggerScroll = () => window.dispatchEvent(new window.Event("scroll"));

let originalGetComputedStyle;
let originalGetBoundingClientRect;

beforeEach(() => {
  render();
  document.documentElement.dataset.theme = "";
  document.documentElement.style.colorScheme = "";
  window.bootstrap = undefined;
  Object.defineProperty(window, "scrollY", { writable: true, value: 0 });
  setMatchMedia(false);
  originalGetComputedStyle = window.getComputedStyle;
  originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
});

afterEach(() => {
  window.getComputedStyle = originalGetComputedStyle;
  Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
  delete global.__baseThemeNavInitialized;
});

test("setInitialTheme applies dark when system prefers dark", () => {
  setMatchMedia(true);
  setInitialTheme(window, document);
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(document.documentElement.style.colorScheme).toBe("dark");
});

test("navbar becomes solid after scrolling past threshold", () => {
  render('<nav class="navbar-recipi"></nav>');
  const nav = document.querySelector(".navbar-recipi");
  init();
  expect(nav.classList.contains("navbar-solid")).toBe(false);
  window.scrollY = 50;
  triggerScroll();
  expect(nav.classList.contains("navbar-solid")).toBe(true);
});

test("collapse fallback toggles show state", () => {
  render(`
    <button id="toggle" data-bs-toggle="collapse" data-bs-target="#panel">Toggle</button>
    <div id="panel" class="collapse"></div>
  `);
  const toggle = document.getElementById("toggle");
  const panel = document.getElementById("panel");
  init();
  expect(panel.classList.contains("show")).toBe(false);
  expect(toggle.getAttribute("aria-expanded")).toBeNull();
  toggle.click();
  expect(panel.classList.contains("show")).toBe(true);
  expect(toggle.getAttribute("aria-expanded")).toBe("true");
  toggle.click();
  expect(panel.classList.contains("show")).toBe(false);
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
});

test("theme updates when system preference changes", () => {
  const listeners = [];
  const { mock } = setMatchMedia(false, listeners);
  init();
  expect(document.documentElement.dataset.theme).toBe("light");
  mock.matches = true;
  listeners.forEach((cb) => cb({ matches: true }));
  expect(document.documentElement.dataset.theme).toBe("dark");
});

test("dropdown fallback toggles and closes on outside click", () => {
  render(`
    <div class="dropdown">
      <button id="dd" data-bs-toggle="dropdown">Toggle</button>
      <div id="menu" class="dropdown-menu"></div>
    </div>
    <div id="outside"></div>
  `);
  init();
  const toggle = document.getElementById("dd");
  const menu = document.getElementById("menu");
  const outside = document.getElementById("outside");
  expect(menu.classList.contains("show")).toBe(false);
  toggle.click();
  expect(menu.classList.contains("show")).toBe(true);
  outside.click();
  expect(menu.classList.contains("show")).toBe(false);
});

test("tab fallback switches active tab and pane", () => {
  render(`
    <ul role="tablist">
      <li><a id="tab1" href="#pane1" data-bs-toggle="tab" class="active" aria-selected="true">One</a></li>
      <li><a id="tab2" href="#pane2" data-bs-toggle="tab" aria-selected="false">Two</a></li>
    </ul>
    <div class="tab-content">
      <div id="pane1" class="tab-pane active show"></div>
      <div id="pane2" class="tab-pane"></div>
    </div>
  `);
  init();
  const tab2 = document.getElementById("tab2");
  const pane1 = document.getElementById("pane1");
  const pane2 = document.getElementById("pane2");
  tab2.click();
  expect(tab2.classList.contains("active")).toBe(true);
  expect(tab2.getAttribute("aria-selected")).toBe("true");
  expect(pane1.classList.contains("show")).toBe(false);
  expect(pane2.classList.contains("show")).toBe(true);
});

test("auth labels become placeholders and hide labels", () => {
  render(`
    <div class="auth-card">
      <form>
        <label for="email">Email</label>
        <input id="email" type="email">
      </form>
    </div>
  `);
  init();
  const input = document.getElementById("email");
  const label = document.querySelector("label");
  expect(input.placeholder).toBe("Email");
  expect(label.style.display).toBe("none");
});

test("nav solid toggles off when scrolling back up", () => {
  render('<nav class="navbar-recipi"></nav>');
  const nav = document.querySelector(".navbar-recipi");
  init();
  window.scrollY = 100;
  triggerScroll();
  expect(nav.classList.contains("navbar-solid")).toBe(true);
  window.scrollY = 0;
  triggerScroll();
  expect(nav.classList.contains("navbar-solid")).toBe(false);
});

test("theme sync applies body dataset and listens for changes", () => {
  const listeners = [];
  const { mock } = setMatchMedia(false, listeners);
  document.body.dataset.theme = "";
  init();
  expect(document.body.dataset.theme).toBe("light");
  mock.matches = true;
  listeners.forEach((cb) => cb({ matches: true }));
  expect(document.body.dataset.theme).toBe("dark");
});

test("dashboard filters autosize width", () => {
  window.getComputedStyle = jest.fn().mockImplementation(() => ({
    paddingLeft: "4",
    paddingRight: "6",
    font: "16px Arial"
  }));
  Element.prototype.getBoundingClientRect = jest.fn().mockReturnValue({ width: 80 });
  render(`
    <select class="dashboard-filter-select">
      <option>Short</option>
      <option selected>Very long option text</option>
    </select>
  `);
  init();
  const select = document.querySelector(".dashboard-filter-select");
  expect(select.style.width).toBe("110px");
});

test("initBaseInteractions no-ops safely when window or nav missing", () => {
  expect(() => initBaseInteractions(null)).not.toThrow();
  render('<nav class="navbar-recipi"></nav>');
  init();
  expect(document.querySelector(".navbar-recipi").classList.contains("navbar-solid")).toBe(false);
});

test("setInitialTheme ignores when window or document missing", () => {
  expect(() => setInitialTheme(null, null)).not.toThrow();
});

test("bootstrap presence skips fallbacks gracefully", () => {
  render(`
    <button data-bs-toggle="collapse" data-bs-target="#panel"></button>
    <div id="panel" class="collapse"></div>
    <div class="dropdown"><button data-bs-toggle="dropdown"></button><div class="dropdown-menu"></div></div>
    <ul role="tablist">
      <li><a id="tab1" href="#pane1" data-bs-toggle="tab" class="active" aria-selected="true">One</a></li>
      <li><a id="tab2" href="#pane2" data-bs-toggle="tab" aria-selected="false">Two</a></li>
    </ul>
    <div class="tab-content"><div id="pane1" class="tab-pane active show"></div><div id="pane2" class="tab-pane"></div></div>
  `);
  window.bootstrap = { Collapse: function () {}, Dropdown: function () {}, Tab: function () {} };
  expect(() => init()).not.toThrow();
  expect(document.querySelector("#pane1").classList.contains("show")).toBe(true);
});

test("falls back without altering existing placeholders and missing tab targets", () => {
  render(`
    <div class="auth-card">
      <form>
        <label for="with-placeholder">With</label>
        <input id="with-placeholder" type="text" placeholder="keep" />
      </form>
    </div>
    <a id="lonely-tab" href="#missing" data-bs-toggle="tab">Missing</a>
    <select class="dashboard-filter-select"><option selected>Test</option></select>
  `);
  window.matchMedia = jest.fn().mockReturnValue({ matches: false });
  setInitialTheme(null, null);
  init();
  document.getElementById("lonely-tab").click();
  expect(document.getElementById("with-placeholder").placeholder).toBe("keep");
});

test("auto init runs on DOMContentLoaded when loading", () => {
  const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
  Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
  const addSpy = jest.spyOn(document, "addEventListener");
  jest.resetModules();
  delete global.__baseThemeNavInitialized;
  require("../../static/js/base_theme_nav");
  expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
  addSpy.mock.calls[0][1]();
  if (originalReady) Object.defineProperty(document, "readyState", originalReady);
  addSpy.mockRestore();
});

test("setInitialTheme returns early when provided window lacks document", () => {
  const stubWin = {};
  setInitialTheme(stubWin);
  expect(document.documentElement.dataset.theme).toBe("");
});
