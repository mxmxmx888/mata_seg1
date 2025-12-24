const modulePath = "../../static/js/edit_profile_modal";

function loadModule() {
  jest.resetModules();
  delete global.__editProfileModalInitialized;
  const mod = require(modulePath);
  delete global.__editProfileModalInitialized;
  return mod;
}

function buildBaseDom({ showOnLoad = false } = {}) {
  document.body.innerHTML = `
    <div id="editProfileModal" ${showOnLoad ? 'data-show-on-load="1"' : ""} aria-hidden="true">
      <div id="editProfileModalLabel"></div>
      <button data-bs-target="#editProfileModal" id="triggerBtn"></button>
      <div class="edit-profile-nav-item active" data-section="profile">Profile</div>
      <div class="edit-profile-nav-item" data-section="password">Password</div>
      <div class="edit-profile-section" data-section="profile">
        <form id="editProfileForm">
          <input name="full_name" value="Alice" />
          <input type="checkbox" name="cb" />
          <button type="button" class="edit-profile-submit-profile d-none">Save</button>
        </form>
      </div>
      <div class="edit-profile-section d-none" data-section="password">
        <form id="passwordForm">
          <input name="pw" value="" />
          <button type="button" class="edit-profile-submit-password d-none">Update</button>
        </form>
      </div>
      <img data-avatar-image src="avatar.png" />
      <span data-avatar-initial class="d-none">A</span>
      <input data-avatar-input type="file" />
      <input data-remove-avatar-input value="false" />
      <button data-avatar-edit>edit avatar</button>
      <button data-remove-avatar>remove avatar</button>
      <button data-privacy-button>Make private</button>
      <span data-privacy-status></span>
      <input type="checkbox" name="is_private" />
    </div>
  `;
}

describe("edit_profile_modal", () => {
  let originalFileReader;
  let originalAddEventListener;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFileReader = global.FileReader;
    originalAddEventListener = window.addEventListener;
  });

  afterEach(() => {
    global.FileReader = originalFileReader;
    window.addEventListener = originalAddEventListener;
    delete global.bootstrap;
    jest.clearAllMocks();
  });

  test("activates password section and toggles submit buttons", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);

    const passwordNav = document.querySelector('[data-section="password"]');
    passwordNav.click();

    expect(document.querySelector('[data-section="profile"]').classList.contains("active")).toBe(false);
    expect(passwordNav.classList.contains("active")).toBe(true);
    expect(document.querySelector("#editProfileForm").classList.contains("d-none")).toBe(true);
    expect(document.querySelector(".edit-profile-submit-password").classList.contains("d-none")).toBe(true);
  });

  test("dirty tracking shows profile submit button", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);

    const input = document.querySelector('input[name="full_name"]');
    input.value = "Bob";
    input.dispatchEvent(new Event("input"));
    expect(document.querySelector(".edit-profile-submit-profile").classList.contains("d-none")).toBe(false);
  });

  test("privacy toggle updates text and dirty state", async () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);

    const btn = document.querySelector("[data-privacy-button]");
    const status = document.querySelector("[data-privacy-status]");
    expect(status.textContent).toBe("Public");
    btn.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
    document.querySelector('input[name="is_private"]').checked = true;
    delete window.__editProfileModalInitialized;
    initEditProfileModal(window);
    await Promise.resolve();
    expect(status.textContent).toBe("Private");
    expect(document.querySelector('input[name=\"is_private\"]').checked).toBe(true);
  });

  test("avatar change shows image and allows removal", () => {
    buildBaseDom();
    class MockFileReader {
      constructor() {
        this.onload = null;
      }
      readAsDataURL() {
        if (this.onload) {
          this.onload({ target: { result: "data:image/png;base64,abc" } });
        }
      }
    }
    global.FileReader = MockFileReader;

    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);

    const fileInput = document.querySelector("[data-avatar-input]");
    const file = new File(["x"], "pic.png", { type: "image/png" });
    Object.defineProperty(fileInput, "files", { value: [file] });
    fileInput.dispatchEvent(new Event("change"));

    expect(document.querySelector("[data-avatar-image]").classList.contains("d-none")).toBe(false);

    document.querySelector("[data-remove-avatar]").click();
    expect(document.querySelector("[data-avatar-image]").classList.contains("d-none")).toBe(true);
    expect(document.querySelector("[data-avatar-initial]").classList.contains("d-none")).toBe(false);
    expect(document.querySelector("[data-remove-avatar-input]").value).toBe("true");
  });

  test("shows modal on load with bootstrap path", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    const show = jest.fn();
    global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show }) } };
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    jest.runAllTimers();
    expect(show).toHaveBeenCalled();
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
  });

  test("fallback modal path triggers data target click", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    const trigger = document.getElementById("triggerBtn");
    const spy = jest.spyOn(trigger, "dispatchEvent");
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });

    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    jest.runAllTimers();
    expect(spy).toHaveBeenCalled();
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
  });

  test("early exits safely when modal missing or already initialized", () => {
    document.body.innerHTML = ``;
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal(window)).not.toThrow();
    global.__editProfileModalInitialized = true;
    expect(() => initEditProfileModal(window)).not.toThrow();
  });

  test("handles missing section name and avatar change with no file", () => {
    buildBaseDom();
    const nav = document.createElement("div");
    nav.className = "edit-profile-nav-item";
    document.getElementById("editProfileModal").appendChild(nav);

    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    expect(() => nav.click()).not.toThrow();

    const avatarInput = document.querySelector("[data-avatar-input]");
    Object.defineProperty(avatarInput, "files", { value: [], writable: true });
    avatarInput.dispatchEvent(new Event("change"));
    expect(document.querySelector("[data-avatar-image]").classList.contains("d-none")).toBe(false);
  });

  test("open modal fallback when no bootstrap or trigger", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    document.querySelector("[data-avatar-edit]").remove(); // keep primary input though
    const trigger = document.querySelector('[data-bs-target="#editProfileModal"]');
    trigger.remove();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    jest.runAllTimers();
    const modal = document.getElementById("editProfileModal");
    expect(modal.classList.contains("show")).toBe(true);
  });

  test("show-on-load waits for load event when not complete", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
    const addEventSpy = jest.spyOn(window, "addEventListener");
    // remove trigger to force manual fallback path
    const trigger = document.querySelector('[data-bs-target="#editProfileModal"]');
    if (trigger) trigger.remove();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    expect(addEventSpy).toHaveBeenCalledWith("load", expect.any(Function), { once: true });
    addEventSpy.mock.calls[0][1]();
    jest.runAllTimers();
    const modal = document.getElementById("editProfileModal");
    expect(modal.classList.contains("show")).toBe(true);
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
    addEventSpy.mockRestore();
  });
});
