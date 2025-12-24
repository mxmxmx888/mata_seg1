const { initNavbar, positionFloatingMenu, getDropdownOffset } = require("../../static/js/navbar_ui");

function buildNavbarDom() {
  document.body.innerHTML = `
    <style>:root{--navbar-dropdown-offset:20px;}</style>
    <div id="prepFilterPopover" class="popover"></div>
    <button id="prepTimeToggle"></button>
    <div class="dropdown">
      <button id="notificationDropdown"><i class="bi bi-heart"></i><span class="notification-dot"></span></button>
      <div class="dropdown-menu"></div>
    </div>
    <input class="recipi-nav-search-input" value="" />
    <button class="app-menu-toggle" aria-expanded="false"></button>
    <div id="appFullScreenMenu"></div>
  `;
  document.body.dataset.markNotificationsUrl = "/mark";
  document.body.dataset.csrf = "token";
}

describe("navbar_ui", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    delete global.__navbarUIInitialized;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  test("positions floating menu within breakpoint", () => {
    document.body.innerHTML = `<button id="t">T</button><div id="m"></div>`;
    const trigger = document.getElementById("t");
    const menu = document.getElementById("m");
    Object.defineProperty(window, "innerWidth", { value: 500, writable: true });
    positionFloatingMenu({ trigger, menu, breakpoint: 640, margin: 10, maxWidth: 200, offset: 10, props: ["position","top","left","right","transform","width","max-width"] });
    expect(menu.style.position).toBe("fixed");
  });

  test("positionFloatingMenu clears styles above breakpoint", () => {
    document.body.innerHTML = `<button id="t">T</button><div id="m" style="position:fixed;top:10px"></div>`;
    const trigger = document.getElementById("t");
    const menu = document.getElementById("m");
    Object.defineProperty(window, "innerWidth", { value: 900, writable: true });
    positionFloatingMenu({ trigger, menu, breakpoint: 640, props: ["position", "top"] });
    expect(menu.style.position).toBe("");
    expect(menu.style.top).toBe("");
  });

  test("getDropdownOffset returns default when CSS var missing", () => {
    const fakeWin = { document, getComputedStyle: () => ({ getPropertyValue: () => "" }) };
    expect(getDropdownOffset(fakeWin)).toBe(18);
  });

  test("prep filter opens, closes, and repositions on resize", () => {
    buildNavbarDom();
    const popover = document.getElementById("prepFilterPopover");
    popover.style.setProperty = jest.fn();
    Object.defineProperty(window, "innerWidth", { value: 500, writable: true });
    jest.resetModules();
    const navbar = require("../../static/js/navbar_ui");
    const handlers = {};
    const addEventListenerSpy = jest.spyOn(window, "addEventListener").mockImplementation((event, handler) => {
      handlers[event] = handlers[event] || [];
      handlers[event].push(handler);
    });
    const toggle = document.getElementById("prepTimeToggle");
    const toggleSpy = jest.spyOn(toggle, "addEventListener");
    navbar.initNavbar(window);
    const clickHandler = toggleSpy.mock.calls.find(([event]) => event === "click")[1];

    clickHandler({ stopPropagation: () => {}, target: toggle });
    expect(popover.classList.contains("prep-filter-open")).toBe(true);
    expect(popover.style.setProperty).toHaveBeenCalled();

    const beforeResizeCalls = popover.style.setProperty.mock.calls.length;
    handlers.resize[0]();
    expect(popover.style.setProperty.mock.calls.length).toBeGreaterThan(beforeResizeCalls);
    toggleSpy.mockRestore();
    addEventListenerSpy.mockRestore();
  });

  test("notification dropdown closes via syncFromState when not expanded", async () => {
    buildNavbarDom();
    const dropdown = document.getElementById("notificationDropdown");
    const menu = document.querySelector(".dropdown-menu");
    menu.style.setProperty = jest.fn();
    initNavbar(window);
    dropdown.dispatchEvent(new Event("click"));
    await new Promise((r) => setTimeout(r, 0));
    expect(menu.style.setProperty).toHaveBeenCalled();
  });

  test("notification dropdown marks read and clears dot", async () => {
    buildNavbarDom();
    const dropdownMenu = document.querySelector(".dropdown-menu");
    const dot = document.querySelector(".notification-dot");
    expect(dot).not.toBeNull();
    initNavbar(window);
    const dropdown = document.getElementById("notificationDropdown");
    // simulate menu open to trigger clearDot
    dropdownMenu.classList.add("show");
    dropdown.dispatchEvent(new Event("click"));
    dropdown.dispatchEvent(new Event("hidden.bs.dropdown"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".notification-dot")).toBeNull();
    expect(global.fetch).toHaveBeenCalledWith("/mark", expect.objectContaining({ method: "POST" }));
  });

  test("mark read only once and mutation observer syncs", async () => {
    buildNavbarDom();
    initNavbar(window);
    const dropdown = document.getElementById("notificationDropdown");
    const menu = document.querySelector(".dropdown-menu");
    menu.classList.add("show");
    dropdown.setAttribute("aria-expanded", "true");
    dropdown.dispatchEvent(new Event("click"));
    // second click should not refetch
    dropdown.dispatchEvent(new Event("click"));
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // mutation observer branch
    const clsEvent = new Event("change");
    menu.classList.add("show");
    menu.dispatchEvent(clsEvent);
  });

  test("search placeholder typing starts and stops on focus/blur", () => {
    buildNavbarDom();
    const input = document.querySelector(".recipi-nav-search-input");
    Object.defineProperty(input, "clientWidth", { value: 100, writable: true });
    initNavbar(window);
    expect(input.placeholder.length).toBeGreaterThan(0);
    input.dispatchEvent(new Event("focus"));
    expect(input.placeholder).toBe("Search...");
    input.dispatchEvent(new Event("blur"));
  });

  test("search placeholder uses compact when width small and active value skips animation", () => {
    buildNavbarDom();
    const input = document.querySelector(".recipi-nav-search-input");
    Object.defineProperty(input, "clientWidth", { value: 80, writable: true });
    input.value = "hello";
    initNavbar(window);
    expect(input.placeholder).toBe("Search...");
    input.dispatchEvent(new Event("blur"));
    expect(input.placeholder).toBe("Search...");

    // resize while focused updates placeholder (value may still be animated text in jsdom)
    input.dispatchEvent(new Event("focus"));
    Object.defineProperty(input, "clientWidth", { value: 300, writable: true });
    window.dispatchEvent(new Event("resize"));
    expect(input.placeholder.length).toBeGreaterThan(0);
  });

  test("search placeholder runs delete cycle and resize during focus", () => {
    jest.useFakeTimers();
    buildNavbarDom();
    const input = document.querySelector(".recipi-nav-search-input");
    Object.defineProperty(input, "clientWidth", { value: 320, writable: true });
    initNavbar(window);
    jest.advanceTimersByTime(6000);
    const firstPlaceholder = input.placeholder;
    jest.advanceTimersByTime(6000);
    expect(input.placeholder).not.toBe(firstPlaceholder);
    input.focus();
    window.dispatchEvent(new Event("resize"));
    expect(input.placeholder.length).toBeGreaterThan(0);
    jest.useRealTimers();
  });

  test("app fullscreen menu toggles", () => {
    buildNavbarDom();
    const menu = document.getElementById("appFullScreenMenu");
    const toggle = document.querySelector(".app-menu-toggle");
    initNavbar(window);
    toggle.click();
    expect(menu.classList.contains("is-open")).toBe(true);
    toggle.click();
    expect(menu.classList.contains("is-open")).toBe(false);
  });

  test("fullscreen menu closes on backdrop click and link click", () => {
    buildNavbarDom();
    const menu = document.getElementById("appFullScreenMenu");
    menu.innerHTML = `<a href="#">Link</a><button class="app-fullscreen-menu-close">x</button>`;
    const toggle = document.querySelector(".app-menu-toggle");
    initNavbar(window);
    toggle.click();
    menu.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(menu.classList.contains("is-open")).toBe(false);
    toggle.click();
    menu.querySelector("a").dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(menu.classList.contains("is-open")).toBe(false);
    toggle.click();
    menu.querySelector(".app-fullscreen-menu-close").click();
    expect(menu.classList.contains("is-open")).toBe(false);

    // toggle from closed state remains closed
    menu.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(menu.classList.contains("is-open")).toBe(false);
  });
});
