(function (global) {
  function initCollectionDetail(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__collectionDetailInitialized) return;
    w.__collectionDetailInitialized = true;

    const doc = w.document;
    const editBtn = doc.getElementById("edit-collection-button");
    const deleteBtn = doc.getElementById("delete-collection-button");
    const editModalEl = doc.getElementById("editCollectionModal");
    const editForm = doc.getElementById("edit-collection-form");
    const titleInput = doc.getElementById("edit-collection-title");
    const closeBtn = editModalEl ? editModalEl.querySelector(".save-modal-close") : null;
    const hasBootstrapModal = !!(w.bootstrap && w.bootstrap.Modal);
    const csrfTokenInput = doc.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfTokenInput ? csrfTokenInput.value : "";

    const collectionId = editBtn ? editBtn.getAttribute("data-collection-id") : "";
    const editEndpoint = editBtn ? editBtn.getAttribute("data-edit-endpoint") : "";
    const deleteEndpoint = deleteBtn ? deleteBtn.getAttribute("data-delete-endpoint") : "";

    let editModalInstance = null;
    let fallbackBackdrop = null;

    function showEditModal() {
      if (!editModalEl) return;
      if (editBtn && titleInput) {
        const currentTitle = editBtn.getAttribute("data-collection-title") || "";
        titleInput.value = currentTitle;
      }
      if (hasBootstrapModal) {
        editModalInstance = w.bootstrap.Modal.getOrCreateInstance(editModalEl);
        editModalInstance.show();
      } else {
        if (!fallbackBackdrop) {
          fallbackBackdrop = doc.createElement("div");
          fallbackBackdrop.className = "modal-backdrop custom-modal-backdrop fade show";
          doc.body.appendChild(fallbackBackdrop);
        }
        editModalEl.classList.add("show");
        editModalEl.style.display = "block";
        editModalEl.removeAttribute("aria-hidden");
        doc.body.classList.add("modal-open");
      }
    }

    function hideEditModal() {
      if (!editModalEl) return;
      if (hasBootstrapModal && editModalInstance) {
        editModalInstance.hide();
      } else {
        if (fallbackBackdrop) {
          fallbackBackdrop.remove();
          fallbackBackdrop = null;
        }
        editModalEl.classList.remove("show");
        editModalEl.style.display = "none";
        editModalEl.setAttribute("aria-hidden", "true");
        doc.body.classList.remove("modal-open");
      }
    }

    if (editBtn && editForm && titleInput) {
      editBtn.addEventListener("click", (e) => {
        e.preventDefault();
        showEditModal();
      });

      editForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newTitle = (titleInput.value || "").trim();
        if (!newTitle) {
          titleInput.focus();
          return;
        }

        const body = new w.URLSearchParams({ name: newTitle, title: newTitle }).toString();

        w
          .fetch(editEndpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
              "X-CSRFToken": csrfToken,
              "X-Requested-With": "XMLHttpRequest"
            },
            body
          })
          .then((resp) => (resp.ok ? resp.json().catch(() => null) : null))
          .then((data) => {
            const updatedTitle = data && data.title ? data.title : newTitle;
            doc.querySelectorAll(".collection-title").forEach((el) => {
              el.textContent = updatedTitle;
            });
            if (editBtn) {
              editBtn.setAttribute("data-collection-title", updatedTitle);
            }
            hideEditModal();
          })
          .catch(() => {
            hideEditModal();
          });
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        hideEditModal();
      });
    }

    if (editModalEl) {
      editModalEl.addEventListener("click", (e) => {
        if (e.target === editModalEl) {
          hideEditModal();
        }
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const confirmed = w.confirm("Delete this collection? This cannot be undone.");
        if (!confirmed) return;

        const body = new w.URLSearchParams({ id: collectionId }).toString();

        w
          .fetch(deleteEndpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
              "X-CSRFToken": csrfToken,
              "X-Requested-With": "XMLHttpRequest"
            },
            body
          })
          .then((resp) => (resp.ok ? resp.json().catch(() => null) : null))
          .then(() => {
            w.location.href = (deleteBtn && deleteBtn.getAttribute("data-redirect-url")) || "/collections/";
          })
          .catch(() => {
            w.location.href = (deleteBtn && deleteBtn.getAttribute("data-redirect-url")) || "/collections/";
          });
      });
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initCollectionDetail };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initCollectionDetail(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
