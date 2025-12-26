const path = "../../static/js/profile_scripts";

function loadModule() {
  jest.resetModules();
  delete global.__profileScriptsInitialized;
  const mod = require(path);
  delete global.__profileScriptsInitialized;
  return mod;
}

describe("profile_scripts modals", () => {
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
    delete global.InfiniteList;
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

    document.querySelector('[data-bs-target="#followersModal"]').click();
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

    document.querySelector('[data-bs-target="#closeFriendsModal"]').click();
    jest.runAllTimers();

    const modal = document.getElementById("closeFriendsModal");
    const backdrop = document.querySelector(".custom-modal-backdrop");
    expect(modal.classList.contains("show")).toBe(true);
    expect(backdrop.classList.contains("show")).toBe(true);

    backdrop.click();
    expect(modal.classList.contains("show")).toBe(false);
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
    const trigger = document.querySelector('[data-bs-target="#followingModal"]');
    trigger.click();
    const modal = document.getElementById("followingModal");
    const backdrop = document.querySelector(".custom-modal-backdrop");
    expect(modal.classList.contains("show")).toBe(true);
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
    const buttons = document.querySelectorAll('[data-bs-target="#followersModal"]');
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
});
