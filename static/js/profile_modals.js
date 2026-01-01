{
const globalWindow = typeof window !== "undefined" ? window : {};
  const FOLLOW_MODAL_CONFIGS = [
    ['[data-bs-target="#followersModal"]', "followersModal"],
    ['[data-bs-target="#followingModal"]', "followingModal"],
    ['[data-bs-target="#closeFriendsModal"]', "closeFriendsModal"],
    ['[data-bs-target="#editProfileModal"]', "editProfileModal"],
  ];

  function buildBackdrop(doc) {
    const el = doc.createElement("div");
    el.className = "modal-backdrop fade custom-modal-backdrop";
    doc.body.appendChild(el);
    return el;
  }

  function lockBody(doc, locked) {
    doc.body.classList.toggle("modal-open", locked);
    doc.body.style.overflow = locked ? "hidden" : "";
  }

  function hideFallbackModal(state) {
    if (!state.current) return;
    state.current.classList.remove("show");
    state.current.style.display = "none";
    state.current.setAttribute("aria-hidden", "true");
    if (state.backdrop) {
      state.backdrop.classList.remove("show");
      state.backdrop.style.display = "none";
      state.backdrop.onclick = null;
    }
    lockBody(state.doc, false);
    state.current = null;
  }

  function showFallbackModal(state, modalEl) {
    state.current = modalEl;
    state.backdrop = state.backdrop || buildBackdrop(state.doc);
    state.backdrop.style.display = "block";
    state.w.setTimeout(() => state.backdrop.classList.add("show"), 0);
    modalEl.classList.add("show");
    modalEl.style.display = "block";
    modalEl.removeAttribute("aria-hidden");
    lockBody(state.doc, true);
    state.backdrop.onclick = () => hideFallbackModal(state);
  }

  function createFallbackModalController(w, doc) {
    const state = { w, doc, backdrop: null, current: null };
    return {
      show: (modalEl) => showFallbackModal(state, modalEl),
      hide: () => hideFallbackModal(state),
    };
  }

  function attachFallbackClose(modalCtrl, modalEl) {
    modalEl.addEventListener("click", (event) => {
      if (event.target === modalEl) modalCtrl.hide();
    });
    const closeBtn = modalEl.querySelector("[data-bs-dismiss='modal'], .btn-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", (event) => {
        event.preventDefault();
        modalCtrl.hide();
      });
    }
  }

  function openFollowModal(w, modalCtrl, modalEl, usingBootstrap) {
    if (usingBootstrap) {
      w.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    } else {
      modalCtrl.show(modalEl);
    }
  }

  function wireFollowModal(w, doc, modalCtrl, usingBootstrap, selector, modalId) {
    const buttons = doc.querySelectorAll(selector);
    const modalEl = doc.getElementById(modalId);
    if (!buttons.length || !modalEl) return;
    if (!usingBootstrap) attachFallbackClose(modalCtrl, modalEl);
    buttons.forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        openFollowModal(w, modalCtrl, modalEl, usingBootstrap);
      });
    });
  }

  function wireFollowModals(w, doc, modalCtrl) {
    const usingBootstrap = !!(w.bootstrap && w.bootstrap.Modal);
    FOLLOW_MODAL_CONFIGS.forEach(([selector, modalId]) => {
      wireFollowModal(w, doc, modalCtrl, usingBootstrap, selector, modalId);
    });
  }

  function postFormData(w, form) {
    const url = form.getAttribute("action");
    if (!url) return Promise.resolve(null);
    const formData = new w.FormData(form);
    return w.fetch(url, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
  }

  function handleFollowToggleSubmit(w, form, event) {
    const url = form.getAttribute("action");
    if (!url) return;
    event.preventDefault();
    postFormData(w, form)
      .then((response) => {
        if (!response || !response.ok) {
          form.submit();
          return;
        }
        const li = form.closest("li");
        if (li) li.remove();
      })
      .catch(() => form.submit());
  }

  function bindFollowToggleForm(w, form) {
    const btn = form.querySelector(".follow-toggle-btn");
    const url = form.getAttribute("action");
    if (!btn || !url) return;
    const followingLabel = btn.getAttribute("data-label-following") || "Following";
    const unfollowLabel = btn.getAttribute("data-label-unfollow") || "Unfollow";
    btn.addEventListener("mouseenter", () => {
      btn.textContent = unfollowLabel;
    });
    btn.addEventListener("mouseleave", () => {
      btn.textContent = followingLabel;
    });
    form.addEventListener("submit", (event) => handleFollowToggleSubmit(w, form, event));
  }

  function bindFollowToggles(w, doc) {
    doc.querySelectorAll(".follow-toggle-form").forEach((form) => {
      bindFollowToggleForm(w, form);
    });
  }

  function createListFilter(doc, { inputId, listId, itemSelector }) {
    const searchInput = doc.getElementById(inputId);
    const list = doc.getElementById(listId);
    if (!searchInput || !list) return () => {};
    const apply = () => {
      const term = (searchInput.value || "").trim().toLowerCase();
      list.querySelectorAll(itemSelector).forEach((item) => {
        const name = item.getAttribute("data-name") || "";
        const match = !term || name.indexOf(term) !== -1;
        item.style.display = match ? "" : "none";
      });
    };
    searchInput.addEventListener("input", apply);
    return apply;
  }

  function submitAjaxForm(w, form) {
    const url = form.getAttribute("action");
    if (!url) return Promise.resolve(null);
    return postFormData(w, form).then((response) => {
      if (!response || !response.ok) throw new Error("Request failed");
      return response.json().catch(() => ({}));
    });
  }

  function bindAjaxForm(w, form, onSuccess) {
    if (form.dataset.ajaxBound === "1") return;
    form.dataset.ajaxBound = "1";
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitAjaxForm(w, form)
        .then((payload) => {
          if (typeof onSuccess === "function") {
            onSuccess({ form, url: form.getAttribute("action") || "", payload: payload || {} });
          }
        })
        .catch(() => form.submit());
    });
  }

  function createAjaxModalBinder(w, doc) {
    return (modalId, onSuccess) => {
      const modalEl = doc.getElementById(modalId);
      if (!modalEl) return;
      modalEl.querySelectorAll("form").forEach((form) => bindAjaxForm(w, form, onSuccess));
    };
  }

  function toggleCloseFriendsAction(form, url) {
    const btn = form.querySelector("button");
    const isAdd = url.indexOf("/add/") !== -1;
    const toggled = isAdd ? url.replace("/add/", "/remove/") : url.replace("/remove/", "/add/");
    form.setAttribute("action", toggled);
    if (btn) {
      btn.textContent = isAdd ? "Remove" : "Add";
    }
  }

  function removeFollowListItem(ctx) {
    const li = ctx.form.closest("li");
    if (li) li.remove();
  }

  function createModalSuccessHandlers(applyFilters) {
    const applyCloseFriendsFilter = applyFilters.closeFriends || (() => {});
    const applyFollowersFilter = applyFilters.followers || (() => {});
    const applyFollowingFilter = applyFilters.following || (() => {});
    return {
      closeFriendsModal: (ctx) => {
        toggleCloseFriendsAction(ctx.form, ctx.url);
        applyCloseFriendsFilter();
      },
      followersModal: (ctx) => {
        removeFollowListItem(ctx);
        applyFollowersFilter();
      },
      followingModal: (ctx) => {
        removeFollowListItem(ctx);
        applyFollowingFilter();
      },
    };
  }

  function createProfileFilters(doc) {
    return {
      closeFriends: createListFilter(doc, {
        inputId: "closeFriendsSearch",
        listId: "closeFriendsList",
        itemSelector: ".close-friend-item",
      }),
      followers: createListFilter(doc, {
        inputId: "followersSearch",
        listId: "followersList",
        itemSelector: ".follow-list-item",
      }),
      following: createListFilter(doc, {
        inputId: "followingSearch",
        listId: "followingList",
        itemSelector: ".follow-list-item",
      }),
    };
  }

  function attachAjaxModals(attachAjaxModalForms, modalSuccessHandlers) {
    attachAjaxModalForms("closeFriendsModal", modalSuccessHandlers.closeFriendsModal);
    attachAjaxModalForms("followersModal", modalSuccessHandlers.followersModal);
    attachAjaxModalForms("followingModal", modalSuccessHandlers.followingModal);
  }

  function initProfileModals(w, doc) {
    const modalCtrl = createFallbackModalController(w, doc);
    const filters = createProfileFilters(doc);
    const attachAjaxModalForms = createAjaxModalBinder(w, doc);
    const modalSuccessHandlers = createModalSuccessHandlers(filters);
    wireFollowModals(w, doc, modalCtrl);
    bindFollowToggles(w, doc);
    attachAjaxModals(attachAjaxModalForms, modalSuccessHandlers);
    return { applyCloseFriendsFilter: filters.closeFriends, attachAjaxModalForms, modalSuccessHandlers };
  }

  const api = {
    initProfileModals,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else if (globalWindow) {
    globalWindow.ProfileModals = api;
  }
}
