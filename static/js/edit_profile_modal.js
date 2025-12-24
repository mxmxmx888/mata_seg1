(function (global) {
  function initEditProfileModal(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__editProfileModalInitialized) return;
    w.__editProfileModalInitialized = true;

    const doc = w.document;
    const modal = doc.getElementById("editProfileModal");
    if (!modal) return;

    const shouldShowOnLoad = modal.getAttribute("data-show-on-load") === "1";
    const navItems = modal.querySelectorAll(".edit-profile-nav-item");
    const sections = modal.querySelectorAll(".edit-profile-section");
    const profileForm = modal.querySelector("#editProfileForm");
    const passwordForm = modal.querySelector("#passwordForm");
    const profileSubmit = modal.querySelector(".edit-profile-submit-profile");
    const passwordSubmit = modal.querySelector(".edit-profile-submit-password");
    const modalTitle = modal.querySelector("#editProfileModalLabel");
    const avatarInputs = modal.querySelectorAll("[data-avatar-input]");
    const avatarEditButtons = modal.querySelectorAll("[data-avatar-edit]");
    const primaryAvatarInput = avatarInputs.length ? avatarInputs[0] : null;
    const removeAvatarInput = modal.querySelector("[data-remove-avatar-input]");
    const removeAvatarBtn = modal.querySelector("[data-remove-avatar]");
    const avatarImages = modal.querySelectorAll("[data-avatar-image]");
    const avatarInitials = modal.querySelectorAll("[data-avatar-initial]");
    const privacyButton = modal.querySelector("[data-privacy-button]");
    const privacyStatus = modal.querySelector("[data-privacy-status]");
    const privacyInput = modal.querySelector("input[name='is_private']");
    let initialAvatarUrl = "";

    if (removeAvatarInput && !removeAvatarInput.defaultValue) {
      removeAvatarInput.defaultValue = removeAvatarInput.value || "false";
    }
    avatarImages.forEach((img) => {
      if (!initialAvatarUrl && img.getAttribute("src")) {
        initialAvatarUrl = img.getAttribute("src");
      }
    });

    let currentSection = "profile";
    let profileDirty = false;
    let passwordDirty = false;

    function showAvatarInitial() {
      avatarImages.forEach((img) => {
        img.classList.add("d-none");
        img.removeAttribute("src");
      });
      avatarInitials.forEach((span) => span.classList.remove("d-none"));
      if (removeAvatarBtn) removeAvatarBtn.classList.add("d-none");
    }

    function showAvatarImage(url) {
      if (!url) return;
      avatarImages.forEach((img) => {
        img.src = url;
        img.classList.remove("d-none");
      });
      avatarInitials.forEach((span) => span.classList.add("d-none"));
      if (removeAvatarBtn) removeAvatarBtn.classList.remove("d-none");
    }

    function recomputeDirty() {
      profileDirty = false;
      passwordDirty = false;

      const inspectForm = (form, setter) => {
        if (!form) return;
        form.querySelectorAll("input, textarea, select").forEach((el) => {
          const isCheckbox = el.type === "checkbox" || el.type === "radio";
          const changed = isCheckbox ? el.checked !== el.defaultChecked : el.value !== el.defaultValue;
          if (changed) setter(true);
        });
      };

      inspectForm(profileForm, (val) => {
        profileDirty = profileDirty || val;
      });
      inspectForm(passwordForm, (val) => {
        passwordDirty = passwordDirty || val;
      });
    }

    function syncPrivacyUI() {
      if (!privacyInput || !privacyButton || !privacyStatus) return;
      const isPrivate = privacyInput.checked;
      privacyStatus.textContent = isPrivate ? "Private" : "Public";
      privacyButton.textContent = isPrivate ? "Make public" : "Make private";
    }

    if (privacyButton && privacyInput) {
      privacyButton.addEventListener("click", () => {
        privacyInput.checked = !privacyInput.checked;
        syncPrivacyUI();
        recomputeDirty();
        updateButtons();
      });
      syncPrivacyUI();
    }

    function updateButtons() {
      if (currentSection === "password") {
        if (profileSubmit) profileSubmit.classList.add("d-none");
        if (passwordSubmit) passwordSubmit.classList.toggle("d-none", !passwordDirty);
      } else {
        if (passwordSubmit) passwordSubmit.classList.add("d-none");
        if (profileSubmit) profileSubmit.classList.toggle("d-none", !profileDirty);
      }
    }

    function activateSection(sectionName) {
      currentSection = sectionName;

      navItems.forEach((btn) => {
        const target = btn.getAttribute("data-section");
        btn.classList.toggle("active", target === sectionName);
      });

      sections.forEach((section) => {
        const target = section.getAttribute("data-section");
        section.classList.toggle("d-none", target !== sectionName);
      });

      if (modalTitle) {
        const activeBtn = modal.querySelector(`.edit-profile-nav-item[data-section="${sectionName}"]`);
        if (activeBtn) {
          modalTitle.textContent = activeBtn.textContent.trim();
        }
      }

      if (sectionName === "password") {
        if (profileForm) profileForm.classList.add("d-none");
        if (passwordForm) passwordForm.classList.remove("d-none");
      } else {
        if (profileForm) profileForm.classList.remove("d-none");
        if (passwordForm) passwordForm.classList.add("d-none");
      }

      updateButtons();
    }

    navItems.forEach((btn) => {
      btn.addEventListener("click", () => {
        const sectionName = btn.getAttribute("data-section");
        if (!sectionName) return;
        activateSection(sectionName);
      });
    });

    avatarInputs.forEach((input) => {
      input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        if (file) {
          if (removeAvatarInput) {
            removeAvatarInput.value = removeAvatarInput.defaultValue || "";
          }
          const reader = new w.FileReader();
          reader.onload = (e) => {
            showAvatarImage((e && e.target && e.target.result) || initialAvatarUrl);
            if (removeAvatarBtn) removeAvatarBtn.classList.remove("d-none");
            recomputeDirty();
            updateButtons();
          };
          reader.readAsDataURL(file);
        } else {
          if (removeAvatarInput && removeAvatarInput.value !== removeAvatarInput.defaultValue) {
            removeAvatarInput.value = removeAvatarInput.defaultValue;
          }
          recomputeDirty();
          updateButtons();
        }
      });
    });

    avatarEditButtons.forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        if (primaryAvatarInput) {
          primaryAvatarInput.click();
        }
      });
    });

    if (removeAvatarBtn) {
      removeAvatarBtn.addEventListener("click", (event) => {
        event.preventDefault();
        avatarInputs.forEach((input) => {
          input.value = "";
        });
        if (removeAvatarInput) {
          removeAvatarInput.value = "true";
          removeAvatarInput.defaultValue = removeAvatarInput.defaultValue || "false";
        }
        showAvatarInitial();
        profileDirty = true;
        recomputeDirty();
        updateButtons();
        if (profileSubmit) profileSubmit.classList.remove("d-none");
      });
    }

    function wireDirtyTracking(form) {
      if (!form) return;
      form.querySelectorAll("input, textarea, select").forEach((el) => {
        el.addEventListener("input", () => {
          recomputeDirty();
          updateButtons();
        });
        el.addEventListener("change", () => {
          recomputeDirty();
          updateButtons();
        });
      });
    }

    wireDirtyTracking(profileForm);
    wireDirtyTracking(passwordForm);

    recomputeDirty();
    updateButtons();

    function openEditProfileModal() {
      const bootstrapModal = w.bootstrap && w.bootstrap.Modal;
      if (bootstrapModal) {
        bootstrapModal.getOrCreateInstance(modal).show();
        return;
      }

      const trigger = doc.querySelector('[data-bs-target="#editProfileModal"]');
      if (trigger) {
        trigger.dispatchEvent(new w.Event("click", { bubbles: true, cancelable: true }));
        return;
      }

      modal.classList.add("show");
      modal.style.display = "block";
      modal.removeAttribute("aria-hidden");
      doc.body.classList.add("modal-open");
      doc.body.style.overflow = "hidden";
    }

    if (shouldShowOnLoad) {
      const runShow = () => {
        w.setTimeout(openEditProfileModal, 0);
      };

      if (doc.readyState === "complete") {
        runShow();
      } else {
        w.addEventListener("load", runShow, { once: true });
      }
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initEditProfileModal };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initEditProfileModal(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
