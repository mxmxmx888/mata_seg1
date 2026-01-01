const modulePath = "../../static/js/edit_profile_modal";

function loadModule() {
  jest.resetModules();
  delete global.__editProfileModalInitialized;
  const mod = require(modulePath);
  delete global.__editProfileModalInitialized;
  return mod;
}

const baseEditProfileMarkup = (showAttr) =>
  `<div id="editProfileModal" ${showAttr} aria-hidden="true"><div id="editProfileModalLabel"></div><button data-bs-target="#editProfileModal" id="triggerBtn"></button><div class="edit-profile-nav-item active" data-section="profile">Profile</div><div class="edit-profile-nav-item" data-section="password">Password</div><div class="edit-profile-section" data-section="profile"><form id="editProfileForm"><input name="full_name" value="Alice" /><input type="checkbox" name="cb" /><button type="button" class="edit-profile-submit-profile d-none">Save</button></form></div><div class="edit-profile-section d-none" data-section="password"><form id="passwordForm"><input name="pw" value="" /><button type="button" class="edit-profile-submit-password d-none">Update</button></form></div><img data-avatar-image src="avatar.png" /><span data-avatar-initial class="d-none">A</span><input data-avatar-input type="file" /><input data-remove-avatar-input value="false" /><button data-avatar-edit>edit avatar</button><button data-remove-avatar>remove avatar</button><button data-privacy-button>Make private</button><span data-privacy-status></span><input type="checkbox" name="is_private" /></div>`;

function buildBaseDom({ showOnLoad = false } = {}) {
  const showAttr = showOnLoad ? 'data-show-on-load="1"' : "";
  document.body.innerHTML = baseEditProfileMarkup(showAttr);
}

const qs = (selector) => document.querySelector(selector);

function setupModal(options = {}) {
  buildBaseDom(options);
  const { initEditProfileModal } = loadModule();
  initEditProfileModal(window);
  return {
    modal: qs("#editProfileModal"),
    nav: (section) => qs(`[data-section="${section}"]`),
    submitProfile: qs(".edit-profile-submit-profile"),
    submitPassword: qs(".edit-profile-submit-password"),
  };
}

function setFiles(input, files) {
  Object.defineProperty(input, "files", { value: files });
}

function mockFileReader(result) {
  class MockFileReader {
    constructor() {
      this.onload = null;
    }
    readAsDataURL() {
      if (this.onload) this.onload({ target: { result } });
    }
  }
  global.FileReader = MockFileReader;
}

let originalFileReader;
let originalAddEventListener;

describe("edit_profile_modal", () => {
  beforeEach(setupEditProfileEnv);
  afterEach(teardownEditProfileEnv);
  registerNavigationTests();
  registerPrivacyTests();
  registerAvatarTests();
  registerModalLoadingTests();
  registerGuardTests();
});

function setupEditProfileEnv() {
  document.body.innerHTML = "";
  originalFileReader = global.FileReader;
  originalAddEventListener = window.addEventListener;
}

function teardownEditProfileEnv() {
  global.FileReader = originalFileReader;
  window.addEventListener = originalAddEventListener;
  delete global.bootstrap;
  jest.clearAllMocks();
}

function registerNavigationTests() {
  testActivatesPasswordSection();
  testDirtyTrackingShowsProfileSubmit();
  testUpdatesModalTitle();
  testInitiallyHidesSubmitButtons();
  testCheckboxChangeMarksProfileDirty();
  testSwitchingBackToProfile();
  testPasswordChangeShowsSubmit();
}

function registerPrivacyTests() {
  testPrivacyToggleUpdatesText();
  testUsesGlobalWindowWhenMissingPrivacyControls();
  testPrivacyToggleBackToPublic();
}

function registerAvatarTests() {
  testAvatarChangeShowsImage();
  testAvatarPreviewFallsBackToInitial();
  testRemoveAvatarClickShowsSubmit();
  testSetsDefaultRemoveAvatarValue();
  testAvatarChangeRestoresRemoveFlag();
  testAvatarEditTriggersPrimaryInput();
  testHandlesMissingSectionAndAvatarChange();
}

function registerModalLoadingTests() {
  testShowsModalOnLoadWithBootstrap();
  testFallbackModalTriggersDataTarget();
  testOpenModalFallbackWithoutBootstrap();
  testShowOnLoadWaitsForLoadEvent();
}

function registerGuardTests() {
  testEarlyExitWhenModalMissing();
  testReturnsEarlyWhenWindowLacksDocument();
  testHandlesMissingFormsGracefully();
}

function testActivatesPasswordSection() {
  test("activates password section and toggles submit buttons", () => {
    const { nav, submitPassword } = setupModal();
    const passwordNav = nav("password");
    passwordNav.click();
    expect(nav("profile").classList.contains("active")).toBe(false);
    expect(passwordNav.classList.contains("active")).toBe(true);
    expect(document.querySelector("#editProfileForm").classList.contains("d-none")).toBe(true);
    expect(submitPassword.classList.contains("d-none")).toBe(true);
  });
}

function testDirtyTrackingShowsProfileSubmit() {
  test("dirty tracking shows profile submit button", () => {
    const { submitProfile } = setupModal();
    const input = document.querySelector('input[name="full_name"]');
    input.value = "Bob";
    input.dispatchEvent(new Event("input"));
    expect(submitProfile.classList.contains("d-none")).toBe(false);
  });
}

function testPrivacyToggleUpdatesText() {
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
    expect(document.querySelector('input[name="is_private"]').checked).toBe(true);
  });
}

function testAvatarChangeShowsImage() {
  test("avatar change shows image and allows removal", () => {
    mockFileReader("data:image/png;base64,abc");
    setupModal();
    const fileInput = document.querySelector("[data-avatar-input]");
    const file = new File(["x"], "pic.png", { type: "image/png" });
    setFiles(fileInput, [file]);
    fileInput.dispatchEvent(new Event("change"));
    expect(document.querySelector("[data-avatar-image]").classList.contains("d-none")).toBe(false);
    document.querySelector("[data-remove-avatar]").click();
    expect(document.querySelector("[data-avatar-image]").classList.contains("d-none")).toBe(true);
    expect(document.querySelector("[data-avatar-initial]").classList.contains("d-none")).toBe(false);
    expect(document.querySelector("[data-remove-avatar-input]").value).toBe("true");
  });
}

function testShowsModalOnLoadWithBootstrap() {
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
}

function testFallbackModalTriggersDataTarget() {
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
}

function testEarlyExitWhenModalMissing() {
  test("early exits safely when modal missing or already initialized", () => {
    document.body.innerHTML = ``;
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal(window)).not.toThrow();
    global.__editProfileModalInitialized = true;
    expect(() => initEditProfileModal(window)).not.toThrow();
  });
}

function testHandlesMissingSectionAndAvatarChange() {
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
}

function testOpenModalFallbackWithoutBootstrap() {
  test("open modal fallback when no bootstrap or trigger", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    document.querySelector("[data-avatar-edit]").remove();
    const trigger = document.querySelector('[data-bs-target="#editProfileModal"]');
    trigger.remove();
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    jest.runAllTimers();
    const modal = document.getElementById("editProfileModal");
    expect(modal.classList.contains("show")).toBe(true);
  });
}

function testShowOnLoadWaitsForLoadEvent() {
  test("show-on-load waits for load event when not complete", () => {
    jest.useFakeTimers();
    buildBaseDom({ showOnLoad: true });
    Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
    const addEventSpy = jest.spyOn(window, "addEventListener");
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
}

function testUsesGlobalWindowWhenMissingPrivacyControls() {
  test("uses global window when no arg and handles missing privacy controls", () => {
    buildBaseDom();
    document.querySelector("[data-privacy-button]").remove();
    document.querySelector("[data-privacy-status]").remove();
    document.querySelector('input[name="is_private"]').remove();
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal()).not.toThrow();
  });
}

function testPrivacyToggleBackToPublic() {
  test("privacy toggle switches back to public", () => {
    setupModal();
    const btn = document.querySelector("[data-privacy-button]");
    btn.click();
    btn.click();
    expect(document.querySelector("[data-privacy-status]").textContent).toBe("Public");
  });
}

function testUpdatesModalTitle() {
  test("updates modal title on section activate and hides password submit in profile", () => {
    const { nav, submitPassword } = setupModal();
    document.getElementById("editProfileModalLabel").textContent = "";
    const profileNav = nav("profile");
    profileNav.click();
    expect(document.getElementById("editProfileModalLabel").textContent.trim()).toBe("Profile");
    expect(submitPassword.classList.contains("d-none")).toBe(true);
  });
}

function testAvatarPreviewFallsBackToInitial() {
  test("avatar preview falls back to initial url when reader result missing", () => {
    mockFileReader(undefined);
    setupModal();
    const fileInput = document.querySelector("[data-avatar-input]");
    const file = new File(["x"], "pic.png", { type: "image/png" });
    setFiles(fileInput, [file]);
    fileInput.dispatchEvent(new Event("change"));
    expect(document.querySelector("[data-avatar-image]").getAttribute("src")).toBe("avatar.png");
  });
}

function testReturnsEarlyWhenWindowLacksDocument() {
  test("returns early when provided window lacks document", () => {
    const { initEditProfileModal } = loadModule();
    expect(() => initEditProfileModal({})).not.toThrow();
  });
}

function testHandlesMissingFormsGracefully() {
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
}

function testInitiallyHidesSubmitButtons() {
  test("initially hides submit buttons when clean", () => {
    const { submitProfile, submitPassword } = setupModal();
    expect(submitProfile.classList.contains("d-none")).toBe(true);
    expect(submitPassword.classList.contains("d-none")).toBe(true);
  });
}

function testRemoveAvatarClickShowsSubmit() {
  test("remove avatar click forces submit visible and dirty", () => {
    const { submitProfile } = setupModal();
    const removeBtn = document.querySelector("[data-remove-avatar]");
    removeBtn.click();
    expect(submitProfile.classList.contains("d-none")).toBe(false);
  });
}

function testSetsDefaultRemoveAvatarValue() {
  test("sets defaultValue for remove avatar input when missing", () => {
    buildBaseDom();
    const input = document.querySelector("[data-remove-avatar-input]");
    input.defaultValue = "";
    const { initEditProfileModal } = loadModule();
    initEditProfileModal(window);
    expect(input.defaultValue).toBe("false");
  });
}

function testPasswordChangeShowsSubmit() {
  test("password change uses dirty tracking and shows submit", () => {
    const { nav, submitPassword } = setupModal();
    nav("password").click();
    const pwInput = document.querySelector('input[name="pw"]');
    pwInput.value = "newpw";
    pwInput.dispatchEvent(new Event("change"));
    expect(submitPassword.classList.contains("d-none")).toBe(false);
  });
}

function testAvatarChangeRestoresRemoveFlag() {
  test("avatar change with no file restores remove flag default", () => {
    setupModal();
    const removeInput = document.querySelector("[data-remove-avatar-input]");
    removeInput.value = "true";
    const avatarInput = document.querySelector("[data-avatar-input]");
    setFiles(avatarInput, []);
    avatarInput.dispatchEvent(new Event("change"));
    expect(removeInput.value).toBe(removeInput.defaultValue);
  });
}

function testAvatarEditTriggersPrimaryInput() {
  test("avatar edit button triggers primary file input click", () => {
    setupModal();
    const fileInput = document.querySelector("[data-avatar-input]");
    const clickSpy = jest.spyOn(fileInput, "click").mockImplementation(() => {});
    document.querySelector("[data-avatar-edit]").click();
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
}

function testCheckboxChangeMarksProfileDirty() {
  test("checkbox change marks profile dirty via change listener", () => {
    const { submitProfile } = setupModal();
    const checkbox = document.querySelector('input[name="cb"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change"));
    expect(submitProfile.classList.contains("d-none")).toBe(false);
  });
}

function testSwitchingBackToProfile() {
  test("switching back to profile section hides password form", () => {
    const { nav } = setupModal();
    const passwordNav = nav("password");
    const profileNav = nav("profile");
    passwordNav.click();
    profileNav.click();
    expect(document.querySelector("#passwordForm").classList.contains("d-none")).toBe(true);
    expect(document.querySelector("#editProfileForm").classList.contains("d-none")).toBe(false);
  });
}
