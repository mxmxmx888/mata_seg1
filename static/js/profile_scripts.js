(function (global) {
  function initProfileScripts(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__profileScriptsInitialized) return;
    w.__profileScriptsInitialized = true;

    const doc = w.document;
    const usingBootstrap = !!(w.bootstrap && w.bootstrap.Modal);
    let fallbackBackdrop = null;
    let currentFallbackModal = null;

    function ensureBackdrop() {
      if (fallbackBackdrop) return fallbackBackdrop;
      const el = doc.createElement("div");
      el.className = "modal-backdrop fade custom-modal-backdrop";
      doc.body.appendChild(el);
      fallbackBackdrop = el;
      return el;
    }

    function showFallbackModal(modalEl) {
      currentFallbackModal = modalEl;
      const backdrop = ensureBackdrop();
      backdrop.style.display = "block";
      w.setTimeout(() => {
        backdrop.classList.add("show");
      }, 0);

      modalEl.classList.add("show");
      modalEl.style.display = "block";
      modalEl.removeAttribute("aria-hidden");

      doc.body.classList.add("modal-open");
      doc.body.style.overflow = "hidden";

      backdrop.onclick = () => hideFallbackModal();
    }

    function hideFallbackModal() {
      if (!currentFallbackModal) return;

      currentFallbackModal.classList.remove("show");
      currentFallbackModal.style.display = "none";
      currentFallbackModal.setAttribute("aria-hidden", "true");

      if (fallbackBackdrop) {
        fallbackBackdrop.classList.remove("show");
        fallbackBackdrop.style.display = "none";
        fallbackBackdrop.onclick = null;
      }

      doc.body.classList.remove("modal-open");
      doc.body.style.overflow = "";
      currentFallbackModal = null;
    }

    function wireFollowModal(buttonSelector, modalId) {
      const buttons = doc.querySelectorAll(buttonSelector);
      const modalEl = doc.getElementById(modalId);
      if (!buttons.length || !modalEl) return;

      if (!usingBootstrap) {
        modalEl.addEventListener("click", (event) => {
          if (event.target === modalEl) {
            hideFallbackModal();
          }
        });

        const closeBtn = modalEl.querySelector("[data-bs-dismiss='modal'], .btn-close");
        if (closeBtn) {
          closeBtn.addEventListener("click", (event) => {
            event.preventDefault();
            hideFallbackModal();
          });
        }
      }

      buttons.forEach((btn) => {
        btn.addEventListener("click", (event) => {
          event.preventDefault();
          if (usingBootstrap) {
            const instance = w.bootstrap.Modal.getOrCreateInstance(modalEl);
            instance.show();
          } else {
            showFallbackModal(modalEl);
          }
        });
      });
    }

    wireFollowModal('[data-bs-target="#followersModal"]', "followersModal");
    wireFollowModal('[data-bs-target="#followingModal"]', "followingModal");
    wireFollowModal('[data-bs-target="#closeFriendsModal"]', "closeFriendsModal");
    wireFollowModal('[data-bs-target="#editProfileModal"]', "editProfileModal");

    doc.querySelectorAll(".follow-toggle-form").forEach((form) => {
      const btn = form.querySelector(".follow-toggle-btn");
      if (!btn) return;

      const followingLabel = btn.getAttribute("data-label-following") || "Following";
      const unfollowLabel = btn.getAttribute("data-label-unfollow") || "Unfollow";

      btn.addEventListener("mouseenter", () => {
        btn.textContent = unfollowLabel;
      });

      btn.addEventListener("mouseleave", () => {
        btn.textContent = followingLabel;
      });

      form.addEventListener("submit", (event) => {
        event.preventDefault();

        const url = form.getAttribute("action");
        if (!url) return;

        const formData = new w.FormData(form);

        w
          .fetch(url, {
            method: "POST",
            body: formData,
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            },
            credentials: "same-origin"
          })
          .then((response) => {
            if (response.ok) {
              const li = form.closest("li");
              if (li) {
                li.remove();
              }
            }
          })
          .catch(() => {
            form.submit();
          });
      });
    });

    const searchInput = doc.getElementById("closeFriendsSearch");
    const list = doc.getElementById("closeFriendsList");
    if (searchInput && list) {
      const items = list.querySelectorAll(".close-friend-item");
      searchInput.addEventListener("input", () => {
        const term = searchInput.value.trim().toLowerCase();
        items.forEach((item) => {
          const name = item.getAttribute("data-name") || "";
          const match = !term || name.indexOf(term) !== -1;
          item.style.display = match ? "" : "none";
        });
      });
    }

    function attachAjaxModalForms(modalId, onSuccess) {
      const modalEl = doc.getElementById(modalId);
      if (!modalEl) return;

      modalEl.querySelectorAll("form").forEach((form) => {
        if (form.dataset.ajaxBound === "1") return;
        form.dataset.ajaxBound = "1";

        form.addEventListener("submit", (event) => {
          event.preventDefault();
          const url = form.getAttribute("action");
          if (!url) return;

          const formData = new w.FormData(form);

          w
            .fetch(url, {
              method: "POST",
              body: formData,
              headers: { "X-Requested-With": "XMLHttpRequest" },
              credentials: "same-origin"
            })
            .then((response) => {
              if (!response.ok) {
                throw new Error("Request failed");
              }
              return response.json().catch(() => {
                return {};
              });
            })
            .then((payload) => {
              if (typeof onSuccess === "function") {
                onSuccess({ form, url, payload: payload || {} });
              }
            })
            .catch(() => {
              form.submit();
            });
        });
      });
    }

    attachAjaxModalForms("closeFriendsModal", (ctx) => {
      const form = ctx.form;
      const url = ctx.url;
      const btn = form.querySelector("button");
      const isAdd = url.indexOf("/add/") !== -1;
      const toggled = isAdd ? url.replace("/add/", "/remove/") : url.replace("/remove/", "/add/");
      form.setAttribute("action", toggled);
      if (btn) {
        btn.textContent = isAdd ? "Remove" : "Add";
      }
    });

    attachAjaxModalForms("followersModal", (ctx) => {
      const li = ctx.form.closest("li");
      if (li) li.remove();
    });

    attachAjaxModalForms("followingModal", (ctx) => {
      const li = ctx.form.closest("li");
      if (li) li.remove();
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initProfileScripts };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initProfileScripts(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
