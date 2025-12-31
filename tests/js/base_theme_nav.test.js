const { setInitialTheme, initBaseInteractions } = require("../../static/js/base_theme_nav");

describe("base_theme_nav", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    document.documentElement.dataset.theme = "";
    document.documentElement.style.colorScheme = "";
    window.bootstrap = undefined;
    Object.defineProperty(window, "scrollY", { writable: true, value: 0 });
    window.matchMedia = jest.fn().mockReturnValue({
      matches: false,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    });
  });

  test("setInitialTheme applies dark when system prefers dark", () => {
    window.matchMedia = jest.fn().mockReturnValue({
      matches: true,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    });

    setInitialTheme(window, document);

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  test("navbar becomes solid after scrolling past threshold", () => {
    document.body.innerHTML = '<nav class="navbar-recipi"></nav>';
    const nav = document.querySelector(".navbar-recipi");

    initBaseInteractions(window);

    expect(nav.classList.contains("navbar-solid")).toBe(false);

    window.scrollY = 50;
    window.dispatchEvent(new window.Event("scroll"));

    expect(nav.classList.contains("navbar-solid")).toBe(true);
  });

  test("collapse fallback toggles show state", () => {
    document.body.innerHTML = `
      <button id="toggle" data-bs-toggle="collapse" data-bs-target="#panel">Toggle</button>
      <div id="panel" class="collapse"></div>
    `;
    const toggle = document.getElementById("toggle");
    const panel = document.getElementById("panel");

    initBaseInteractions(window);

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
    const mockPrefers = {
      matches: false,
      addEventListener: (name, cb) => listeners.push(cb),
      removeEventListener: jest.fn()
    };
    window.matchMedia = jest.fn().mockImplementation(() => mockPrefers);

    initBaseInteractions(window);

    expect(document.documentElement.dataset.theme).toBe("light");

    mockPrefers.matches = true;
    listeners.forEach((cb) => cb({ matches: true }));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  test("dropdown fallback toggles and closes on outside click", () => {
    document.body.innerHTML = `
      <div class="dropdown">
        <button id="dd" data-bs-toggle="dropdown">Toggle</button>
        <div id="menu" class="dropdown-menu"></div>
      </div>
      <div id="outside"></div>
    `;

    initBaseInteractions(window);

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
    document.body.innerHTML = `
      <ul role="tablist">
        <li><a id="tab1" href="#pane1" data-bs-toggle="tab" class="active" aria-selected="true">One</a></li>
        <li><a id="tab2" href="#pane2" data-bs-toggle="tab" aria-selected="false">Two</a></li>
      </ul>
      <div class="tab-content">
        <div id="pane1" class="tab-pane active show"></div>
        <div id="pane2" class="tab-pane"></div>
      </div>
    `;

    initBaseInteractions(window);

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
    document.body.innerHTML = `
      <div class="auth-card">
        <form>
          <label for="email">Email</label>
          <input id="email" type="email">
        </form>
      </div>
    `;

    initBaseInteractions(window);

    const input = document.getElementById("email");
    const label = document.querySelector("label");
    expect(input.placeholder).toBe("Email");
    expect(label.style.display).toBe("none");
  });

  test("nav solid toggles off when scrolling back up", () => {
    document.body.innerHTML = '<nav class="navbar-recipi"></nav>';
    const nav = document.querySelector(".navbar-recipi");
    initBaseInteractions(window);
    window.scrollY = 100;
    window.dispatchEvent(new window.Event("scroll"));
    expect(nav.classList.contains("navbar-solid")).toBe(true);
    window.scrollY = 0;
    window.dispatchEvent(new window.Event("scroll"));
    expect(nav.classList.contains("navbar-solid")).toBe(false);
  });

  test("theme sync applies body dataset and listens for changes", () => {
    const listeners = [];
    const mockPref = {
      matches: false,
      addEventListener: (event, cb) => listeners.push(cb),
      removeEventListener: jest.fn()
    };
    window.matchMedia = jest.fn().mockReturnValue(mockPref);
    document.body.dataset.theme = "";

    initBaseInteractions(window);

    expect(document.body.dataset.theme).toBe("light");
    mockPref.matches = true;
    listeners.forEach((cb) => cb());
    expect(document.body.dataset.theme).toBe("dark");
  });

  test("dashboard filters autosize width", () => {
    const originalGetComputedStyle = window.getComputedStyle;
    window.getComputedStyle = jest.fn().mockImplementation((el) => ({
      paddingLeft: "4",
      paddingRight: "6",
      font: "16px Arial"
    }));

    document.body.innerHTML = `
      <select class="dashboard-filter-select">
        <option>Short</option>
        <option selected>Very long option text</option>
      </select>
    `;

    // Mock measure width for spans created during autosize.
    const rectMock = { width: 80 };
    const originalGetBounding = Element.prototype.getBoundingClientRect;
    const boundingSpy = jest.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue(rectMock);

    initBaseInteractions(window);

    const select = document.querySelector(".dashboard-filter-select");
    const initialCalls = boundingSpy.mock.calls.length;

    select.dispatchEvent(new Event("change"));

    expect(parseFloat(select.style.width)).toBeGreaterThan(0);
    expect(boundingSpy.mock.calls.length).toBeGreaterThan(initialCalls);

    // Restore mocks
    window.getComputedStyle = originalGetComputedStyle;
    Element.prototype.getBoundingClientRect = originalGetBounding;
  });

  test("initBaseInteractions no-ops safely when window or nav missing", () => {
    expect(() => initBaseInteractions(null)).not.toThrow();
    document.body.classList.add("auth-body");
    document.body.innerHTML = `<nav class="navbar-recipi"></nav>`;
    initBaseInteractions(window);
    expect(document.querySelector(".navbar-recipi").classList.contains("navbar-solid")).toBe(false);
  });

  test("setInitialTheme ignores when window or document missing", () => {
    expect(() => setInitialTheme(null, null)).not.toThrow();
  });

  test("bootstrap presence skips fallbacks gracefully", () => {
    document.body.innerHTML = `
      <button data-bs-toggle="collapse" data-bs-target="#panel"></button>
      <div id="panel" class="collapse"></div>
      <div class="dropdown"><button data-bs-toggle="dropdown"></button><div class="dropdown-menu"></div></div>
      <ul role="tablist">
        <li><a id="tab1" href="#pane1" data-bs-toggle="tab" class="active" aria-selected="true">One</a></li>
        <li><a id="tab2" href="#pane2" data-bs-toggle="tab" aria-selected="false">Two</a></li>
      </ul>
      <div class="tab-content">
        <div id="pane1" class="tab-pane active show"></div>
        <div id="pane2" class="tab-pane"></div>
      </div>
    `;
    window.bootstrap = {
      Collapse: function () {},
      Dropdown: function () {},
      Tab: function () {}
    };
    expect(() => initBaseInteractions(window)).not.toThrow();
    // fallbacks should not toggle classes when bootstrap present
    expect(document.querySelector("#pane1").classList.contains("show")).toBe(true);
  });

  test("covers fallback branches and existing placeholders", () => {
    document.body.innerHTML = `
      <div class="auth-card">
        <form>
          <label for="with-placeholder">With</label>
          <input id="with-placeholder" type="text" placeholder="keep" />
        </form>
      </div>
      <a id="lonely-tab" href="#missing" data-bs-toggle="tab">Missing</a>
      <select class="dashboard-filter-select"><option selected>Test</option></select>
    `;
    window.matchMedia = jest.fn().mockReturnValue({ matches: false });
    const originalGetComputedStyle = window.getComputedStyle;
    window.getComputedStyle = jest.fn().mockReturnValue({});
    setInitialTheme(null, null);
    initBaseInteractions(window);
    // clicking tab without tablist/tabContent should no-op
    document.getElementById("lonely-tab").click();
    expect(document.getElementById("with-placeholder").placeholder).toBe("keep");
    window.getComputedStyle = originalGetComputedStyle;
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
    if (originalReady) {
      Object.defineProperty(document, "readyState", originalReady);
    }
    addSpy.mockRestore();
  });

  test("setInitialTheme and initBaseInteractions handle missing window/doc", () => {
    expect(() => setInitialTheme(null, null)).not.toThrow();
    const nav = document.createElement("nav");
    nav.className = "navbar-recipi";
    document.body.appendChild(nav);
    expect(() => initBaseInteractions(null)).not.toThrow();
    expect(() => initBaseInteractions(window)).not.toThrow();
  });

  test("setInitialTheme returns early when provided window lacks document", () => {
    const stubWin = {};
    setInitialTheme(stubWin);
    expect(document.documentElement.dataset.theme).toBe("");
  });
});
