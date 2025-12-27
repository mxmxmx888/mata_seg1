const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const collectAvatarState = (modal) => {
  const avatarInputs = Array.from(modal.querySelectorAll("[data-avatar-input]"));
  const avatarImages = Array.from(modal.querySelectorAll("[data-avatar-image]"));
  const avatarInitials = Array.from(modal.querySelectorAll("[data-avatar-initial]"));
  const primaryAvatarInput = avatarInputs.length ? avatarInputs[0] : null;
  let initialAvatarUrl = "";
  avatarImages.forEach((img) => {
    if (!initialAvatarUrl && img.getAttribute("src")) initialAvatarUrl = img.getAttribute("src");
  });
  const removeAvatarInput = modal.querySelector("[data-remove-avatar-input]");
  if (removeAvatarInput && !removeAvatarInput.defaultValue) {
    removeAvatarInput.defaultValue = removeAvatarInput.value || "false";
  }
  return { avatarInputs, avatarImages, avatarInitials, primaryAvatarInput, removeAvatarInput, initialAvatarUrl };
};

const collectModalElements = (modal) => ({
  navItems: Array.from(modal.querySelectorAll(".edit-profile-nav-item")),
  sections: Array.from(modal.querySelectorAll(".edit-profile-section")),
  profileForm: modal.querySelector("#editProfileForm"),
  passwordForm: modal.querySelector("#passwordForm"),
  profileSubmit: modal.querySelector(".edit-profile-submit-profile"),
  passwordSubmit: modal.querySelector(".edit-profile-submit-password"),
  modalTitle: modal.querySelector("#editProfileModalLabel"),
  removeAvatarBtn: modal.querySelector("[data-remove-avatar]"),
  privacyButton: modal.querySelector("[data-privacy-button]"),
  privacyStatus: modal.querySelector("[data-privacy-status]"),
  privacyInput: modal.querySelector("input[name='is_private']")
});

const buildEditProfileState = (w) => {
  const doc = w.document;
  const modal = doc.getElementById("editProfileModal");
  if (!modal) return null;
  const avatarState = collectAvatarState(modal);
  return {
    w,
    doc,
    modal,
    shouldShowOnLoad: modal.getAttribute("data-show-on-load") === "1",
    currentSection: "profile",
    profileDirty: false,
    passwordDirty: false,
    ...collectModalElements(modal),
    ...avatarState
  };
};

const showAvatarInitial = (state) => {
  state.avatarImages.forEach((img) => {
    img.classList.add("d-none");
    img.removeAttribute("src");
  });
  state.avatarInitials.forEach((span) => span.classList.remove("d-none"));
  if (state.removeAvatarBtn) state.removeAvatarBtn.classList.add("d-none");
};

const showAvatarImage = (state, url) => {
  if (!url) return;
  state.avatarImages.forEach((img) => {
    img.src = url;
    img.classList.remove("d-none");
  });
  state.avatarInitials.forEach((span) => span.classList.add("d-none"));
  if (state.removeAvatarBtn) state.removeAvatarBtn.classList.remove("d-none");
};

const inspectFormDirty = (form) => {
  let dirty = false;
  if (!form) return dirty;
  form.querySelectorAll("input, textarea, select").forEach((el) => {
    const isCheckbox = el.type === "checkbox" || el.type === "radio";
    const changed = isCheckbox ? el.checked !== el.defaultChecked : el.value !== el.defaultValue;
    if (changed) dirty = true;
  });
  return dirty;
};

const recomputeDirty = (state) => {
  state.profileDirty = inspectFormDirty(state.profileForm);
  state.passwordDirty = inspectFormDirty(state.passwordForm);
};

const updateButtons = (state) => {
  if (state.currentSection === "password") {
    if (state.profileSubmit) state.profileSubmit.classList.add("d-none");
    if (state.passwordSubmit) state.passwordSubmit.classList.toggle("d-none", !state.passwordDirty);
  } else {
    if (state.passwordSubmit) state.passwordSubmit.classList.add("d-none");
    if (state.profileSubmit) state.profileSubmit.classList.toggle("d-none", !state.profileDirty);
  }
};

const toggleSectionVisibility = (state, sectionName) => {
  state.navItems.forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-section") === sectionName);
  });
  state.sections.forEach((section) => {
    section.classList.toggle("d-none", section.getAttribute("data-section") !== sectionName);
  });
  if (state.modalTitle) {
    const activeBtn = state.modal.querySelector(`.edit-profile-nav-item[data-section="${sectionName}"]`);
    if (activeBtn) state.modalTitle.textContent = activeBtn.textContent.trim();
  }
  if (sectionName === "password") {
    if (state.profileForm) state.profileForm.classList.add("d-none");
    if (state.passwordForm) state.passwordForm.classList.remove("d-none");
  } else {
    if (state.profileForm) state.profileForm.classList.remove("d-none");
    if (state.passwordForm) state.passwordForm.classList.add("d-none");
  }
};

const activateSection = (state, sectionName) => {
  state.currentSection = sectionName;
  toggleSectionVisibility(state, sectionName);
  updateButtons(state);
};

const bindNavItems = (state) => {
  state.navItems.forEach((btn) => {
    btn.addEventListener("click", () => {
      const sectionName = btn.getAttribute("data-section");
      if (!sectionName) return;
      activateSection(state, sectionName);
    });
  });
};

const setRemoveAvatarFlag = (state, value) => {
  if (!state.removeAvatarInput) return;
  state.removeAvatarInput.value = value;
  state.removeAvatarInput.defaultValue = state.removeAvatarInput.defaultValue || "false";
};

const applyAvatarFromFile = (state, file) => {
  if (!file) return;
  setRemoveAvatarFlag(state, state.removeAvatarInput ? state.removeAvatarInput.defaultValue || "" : "");
  const reader = new state.w.FileReader();
  reader.onload = (e) => {
    showAvatarImage(state, (e && e.target && e.target.result) || state.initialAvatarUrl);
    if (state.removeAvatarBtn) state.removeAvatarBtn.classList.remove("d-none");
    recomputeDirty(state);
    updateButtons(state);
  };
  reader.readAsDataURL(file);
};

const handleAvatarChange = (state, input) => {
  const file = input.files && input.files[0];
  if (file) {
    applyAvatarFromFile(state, file);
    return;
  }
  if (state.removeAvatarInput && state.removeAvatarInput.value !== state.removeAvatarInput.defaultValue) {
    state.removeAvatarInput.value = state.removeAvatarInput.defaultValue;
  }
  recomputeDirty(state);
  updateButtons(state);
};

const bindAvatarInputs = (state) => {
  state.avatarInputs.forEach((input) => {
    input.addEventListener("change", () => handleAvatarChange(state, input));
  });
};

const bindAvatarButtons = (state) => {
  state.modal.querySelectorAll("[data-avatar-edit]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      if (state.primaryAvatarInput) state.primaryAvatarInput.click();
    });
  });
};

const bindRemoveAvatar = (state) => {
  if (!state.removeAvatarBtn) return;
  state.removeAvatarBtn.addEventListener("click", (event) => {
    event.preventDefault();
    state.avatarInputs.forEach((input) => {
      input.value = "";
    });
    setRemoveAvatarFlag(state, "true");
    showAvatarInitial(state);
    state.profileDirty = true;
    recomputeDirty(state);
    updateButtons(state);
    if (state.profileSubmit) state.profileSubmit.classList.remove("d-none");
  });
};

const syncPrivacyUI = (state) => {
  const isPrivate = state.privacyInput.checked;
  if (state.privacyStatus) state.privacyStatus.textContent = isPrivate ? "Private" : "Public";
  if (state.privacyButton) state.privacyButton.textContent = isPrivate ? "Make public" : "Make private";
};

const bindPrivacy = (state) => {
  if (!state.privacyButton || !state.privacyInput || !state.privacyStatus) return;
  state.privacyButton.addEventListener("click", () => {
    state.privacyInput.checked = !state.privacyInput.checked;
    syncPrivacyUI(state);
    recomputeDirty(state);
    updateButtons(state);
  });
  syncPrivacyUI(state);
};

const bindDirtyTracking = (state, form) => {
  if (!form) return;
  form.querySelectorAll("input, textarea, select").forEach((el) => {
    const handle = () => {
      recomputeDirty(state);
      updateButtons(state);
    };
    el.addEventListener("input", handle);
    el.addEventListener("change", handle);
  });
};

const bindDirtyHandlers = (state) => {
  bindDirtyTracking(state, state.profileForm);
  bindDirtyTracking(state, state.passwordForm);
};

const openEditProfileModal = (state) => {
  const bootstrapModal = state.w.bootstrap && state.w.bootstrap.Modal;
  if (bootstrapModal) {
    bootstrapModal.getOrCreateInstance(state.modal).show();
    return;
  }
  const trigger = state.doc.querySelector('[data-bs-target="#editProfileModal"]');
  if (trigger) {
    trigger.dispatchEvent(new state.w.Event("click", { bubbles: true, cancelable: true }));
    return;
  }
  state.modal.classList.add("show");
  state.modal.style.display = "block";
  state.modal.removeAttribute("aria-hidden");
  state.doc.body.classList.add("modal-open");
  state.doc.body.style.overflow = "hidden";
};

const maybeShowOnLoad = (state) => {
  if (!state.shouldShowOnLoad) return;
  const runShow = () => state.w.setTimeout(() => openEditProfileModal(state), 0);
  if (state.doc.readyState === "complete") {
    runShow();
  } else {
    state.w.addEventListener("load", runShow, { once: true });
  }
};

const initEditProfileModal = (win) => {
  const w = resolveWindow(win);
  if (!w) return;
  if (w.__editProfileModalInitialized) return;
  w.__editProfileModalInitialized = true;
  const state = buildEditProfileState(w);
  if (!state) return;
  bindPrivacy(state);
  bindNavItems(state);
  bindAvatarInputs(state);
  bindAvatarButtons(state);
  bindRemoveAvatar(state);
  bindDirtyHandlers(state);
  recomputeDirty(state);
  updateButtons(state);
  maybeShowOnLoad(state);
};

const autoInitEditProfileModal = () => {
  const w = resolveWindow();
  if (!w || !w.document) return;
  const runInit = () => initEditProfileModal(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initEditProfileModal };
}

/* istanbul ignore next */
autoInitEditProfileModal();
