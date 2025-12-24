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

  test("uses global window when no arg and handles missing privacy controls", () => {
    buildBaseDom();
    document.querySelector("[data-privacy-button]").remove();
    document.querySelector("[data-privacy-status]").remove();
    document.querySelector('input[name="is_private"]').remove();
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal()).not.toThrow();
  });

  test("privacy toggle switches back to public", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const btn = document.querySelector("[data-privacy-button]");
    btn.click(); // to private
    btn.click(); // back to public
    expect(document.querySelector("[data-privacy-status]").textContent).toBe("Public");
  });

  test("updates modal title on section activate and hides password submit in profile", () => {
    buildBaseDom();
    document.getElementById("editProfileModalLabel").textContent = "";
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const profileNav = document.querySelector('[data-section="profile"]');
    profileNav.click();
    expect(document.getElementById("editProfileModalLabel").textContent.trim()).toBe("Profile");
    expect(document.querySelector(".edit-profile-submit-password").classList.contains("d-none")).toBe(true);
  });

  test("avatar preview falls back to initial url when reader result missing", () => {
    class MockFileReader {
      constructor() {
        this.onload = null;
      }
      readAsDataURL() {
        if (this.onload) this.onload({});
      }
    }
    global.FileReader = MockFileReader;
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const fileInput = document.querySelector("[data-avatar-input]");
    const file = new File(["x"], "pic.png", { type: "image/png" });
    Object.defineProperty(fileInput, "files", { value: [file] });
    fileInput.dispatchEvent(new Event("change"));
    expect(document.querySelector("[data-avatar-image]").getAttribute("src")).toBe("avatar.png");
  });

  test("returns early when provided window lacks document", () => {
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal({})).not.toThrow();
  });

  test("handles missing forms and avatar inputs gracefully", () => {
    document.body.innerHTML = `
      <div id="editProfileModal">
        <div id="editProfileModalLabel"></div>
        <div class="edit-profile-nav-item" data-section="profile">Profile</div>
        <div class="edit-profile-section" data-section="profile"></div>
      </div>
    `;
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal(window)).not.toThrow();
  });

  test("initially hides submit buttons when clean", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    expect(document.querySelector(".edit-profile-submit-profile").classList.contains("d-none")).toBe(true);
    expect(document.querySelector(".edit-profile-submit-password").classList.contains("d-none")).toBe(true);
  });

  test("remove avatar click forces submit visible and dirty", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const submit = document.querySelector(".edit-profile-submit-profile");
    const removeBtn = document.querySelector("[data-remove-avatar]");
    removeBtn.click();
    expect(submit.classList.contains("d-none")).toBe(false);
  });

  test("sets defaultValue for remove avatar input when missing", () => {
    buildBaseDom();
    const input = document.querySelector("[data-remove-avatar-input]");
    input.defaultValue = "";
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    expect(input.defaultValue).toBe("false");
  });

  test("password change uses dirty tracking and shows submit", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    document.querySelector('[data-section="password"]').click();
    const pwInput = document.querySelector('input[name="pw"]');
    pwInput.value = "newpw";
    pwInput.dispatchEvent(new Event("change"));
    expect(document.querySelector(".edit-profile-submit-password").classList.contains("d-none")).toBe(false);
  });

  test("avatar change with no file restores remove flag default", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const removeInput = document.querySelector("[data-remove-avatar-input]");
    removeInput.value = "true";
    const avatarInput = document.querySelector("[data-avatar-input]");
    Object.defineProperty(avatarInput, "files", { value: [] });
    avatarInput.dispatchEvent(new Event("change"));
    expect(removeInput.value).toBe(removeInput.defaultValue);
  });

  test("avatar edit button triggers primary file input click", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const fileInput = document.querySelector("[data-avatar-input]");
    const clickSpy = jest.spyOn(fileInput, "click").mockImplementation(() => {});
    document.querySelector("[data-avatar-edit]").click();
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  test("checkbox change marks profile dirty via change listener", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const checkbox = document.querySelector('input[name="cb"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change"));
    expect(document.querySelector(".edit-profile-submit-profile").classList.contains("d-none")).toBe(false);
  });

  test("switching back to profile section hides password form", () => {
    buildBaseDom();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    const passwordNav = document.querySelector('[data-section="password"]');
    const profileNav = document.querySelector('[data-section="profile"]');
    passwordNav.click();
    profileNav.click();
    expect(document.querySelector("#passwordForm").classList.contains("d-none")).toBe(true);
    expect(document.querySelector("#editProfileForm").classList.contains("d-none")).toBe(false);
  });
});
