const modulePath = "../../../static/js/edit_profile_modal";

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

module.exports = {
  buildBaseDom,
  loadModule,
  mockFileReader,
  setFiles,
  setupModal,
};
