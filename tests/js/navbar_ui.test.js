const { initNavbar, positionFloatingMenu, getDropdownOffset } = require("../../static/js/navbar_ui");

const buildNavbarDom = () => {
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
};

afterEach(() => {
  document.head.innerHTML = "";
  jest.clearAllMocks();
});

test("positions floating menu within breakpoint and clears above", () => {
  document.body.innerHTML = `<button id="t">T</button><div id="m"></div>`;
  const trigger = document.getElementById("t");
  const menu = document.getElementById("m");
  Object.defineProperty(window, "innerWidth", { value: 500, writable: true });
  positionFloatingMenu({ trigger, menu, breakpoint: 640, margin: 10, maxWidth: 200, offset: 10, props: ["position", "top", "left", "right", "transform", "width", "max-width"] });
  expect(menu.style.position).toBe("fixed");
  Object.defineProperty(window, "innerWidth", { value: 900, writable: true });
  positionFloatingMenu({ trigger, menu, breakpoint: 640, props: ["position", "top"] });
  expect(menu.style.position).toBe("");
});

test("getDropdownOffset uses CSS var or default", () => {
  const style = document.createElement("style");
  style.textContent = `:root { --navbar-dropdown-offset: 42px; }`;
  document.head.appendChild(style);
  expect(getDropdownOffset(window)).toBe(42);
  document.head.removeChild(style);
  expect(getDropdownOffset({ document, getComputedStyle: () => ({ getPropertyValue: () => "" }) })).toBe(18);
});

test("prep filter opens, closes, and repositions on resize", () => {
  buildNavbarDom();
  const popover = document.getElementById("prepFilterPopover");
  popover.style.setProperty = jest.fn();
  Object.defineProperty(window, "innerWidth", { value: 500, writable: true });
  const handlers = {};
  jest.spyOn(window, "addEventListener").mockImplementation((event, handler) => {
    handlers[event] = handlers[event] || [];
    handlers[event].push(handler);
  });
  const toggle = document.getElementById("prepTimeToggle");
  jest.spyOn(toggle, "addEventListener");
  initNavbar(window);
  toggle.dispatchEvent(new Event("click"));
  expect(popover.classList.contains("prep-filter-open")).toBe(true);
  const beforeResize = popover.style.setProperty.mock.calls.length;
  handlers.resize[0]();
  expect(popover.style.setProperty.mock.calls.length).toBeGreaterThan(beforeResize);
});

test("notification dropdown closes via syncFromState and marks read once", async () => {
  global.fetch = jest.fn().mockResolvedValue({ ok: true });
  buildNavbarDom();
  const dropdown = document.getElementById("notificationDropdown");
  const menu = document.querySelector(".dropdown-menu");
  menu.style.setProperty = jest.fn();
  initNavbar(window);
  dropdown.dispatchEvent(new Event("click"));
  await new Promise((r) => setTimeout(r, 0));
  expect(menu.style.setProperty).toHaveBeenCalled();
  menu.classList.add("show");
  dropdown.setAttribute("aria-expanded", "true");
  dropdown.dispatchEvent(new Event("click"));
  dropdown.dispatchEvent(new Event("click"));
  dropdown.dispatchEvent(new Event("hidden.bs.dropdown"));
  await new Promise((r) => setTimeout(r, 0));
  expect(document.querySelector(".notification-dot")).toBeNull();
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

test("search placeholder handles focus/blur, compact width, and resize", () => {
  buildNavbarDom();
  const input = document.querySelector(".recipi-nav-search-input");
  Object.defineProperty(input, "clientWidth", { value: 80, writable: true });
  input.value = "hello";
  initNavbar(window);
  input.dispatchEvent(new Event("focus"));
  expect(input.placeholder).toBe("Search...");
  input.dispatchEvent(new Event("blur"));
  input.dispatchEvent(new Event("focus"));
  Object.defineProperty(input, "clientWidth", { value: 300, writable: true });
  window.dispatchEvent(new Event("resize"));
  expect(input.placeholder.length).toBeGreaterThan(0);
});

test("search placeholder animation cycles", () => {
  jest.useFakeTimers();
  buildNavbarDom();
  const input = document.querySelector(".recipi-nav-search-input");
  Object.defineProperty(input, "clientWidth", { value: 320, writable: true });
  initNavbar(window);
  const first = input.placeholder;
  jest.advanceTimersByTime(6000);
  expect(input.placeholder).not.toBe(first);
  jest.useRealTimers();
});

test("app fullscreen menu toggles and closes on clicks", () => {
  buildNavbarDom();
  const menu = document.getElementById("appFullScreenMenu");
  menu.innerHTML = `<a href="#">Link</a><button class="app-fullscreen-menu-close">x</button>`;
  const toggle = document.querySelector(".app-menu-toggle");
  initNavbar(window);
  toggle.click();
  expect(menu.classList.contains("is-open")).toBe(true);
  menu.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  expect(menu.classList.contains("is-open")).toBe(false);
  toggle.click();
  menu.querySelector("a").dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  expect(menu.classList.contains("is-open")).toBe(false);
  toggle.click();
  menu.querySelector(".app-fullscreen-menu-close").click();
  expect(menu.classList.contains("is-open")).toBe(false);
});

test("initNavbar handles missing window/document and initializes only once", () => {
  expect(() => initNavbar(null)).not.toThrow();
  global.__navbarUIInitialized = true;
  expect(() => initNavbar(window)).not.toThrow();
  delete global.__navbarUIInitialized;
});

test("positionFloatingMenu no-ops without trigger/menu", () => {
  positionFloatingMenu({ trigger: null, menu: null });
  const menu = document.createElement("div");
  menu.style.position = "fixed";
  positionFloatingMenu({ trigger: null, menu, breakpoint: 1, props: ["position"] });
  expect(menu.style.position).toBe("fixed");
});
