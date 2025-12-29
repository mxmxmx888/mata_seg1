{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow || (typeof window !== "undefined" ? window : null);
  return candidate && candidate.document ? candidate : null;
};

const elementRefs = (doc) => ({
  editBtn: doc.getElementById("edit-collection-button"),
  deleteBtn: doc.getElementById("delete-collection-button"),
  editModal: doc.getElementById("editCollectionModal"),
  editForm: doc.getElementById("edit-collection-form"),
  titleInput: doc.getElementById("edit-collection-title"),
  closeBtn: doc.getElementById("editCollectionModal")?.querySelector(".save-modal-close"),
});

const buildCtx = (w) => {
  const doc = w.document;
  const refs = elementRefs(doc);
  const csrfInput = doc.querySelector('input[name="csrfmiddlewaretoken"]');
  return {
    w,
    doc,
    ...refs,
    csrfToken: csrfInput ? csrfInput.value : "",
    collectionId: refs.editBtn?.getAttribute("data-collection-id") || "",
    editEndpoint: refs.editBtn?.getAttribute("data-edit-endpoint") || "",
    deleteEndpoint: refs.deleteBtn?.getAttribute("data-delete-endpoint") || "",
    redirectUrl: refs.deleteBtn?.getAttribute("data-redirect-url") || "/collections/",
    hasBootstrapModal: !!(w.bootstrap && w.bootstrap.Modal),
    editModalInstance: null,
    fallbackBackdrop: null,
  };
};

const ensureFallbackBackdrop = (ctx) => {
  if (ctx.fallbackBackdrop) return ctx.fallbackBackdrop;
  const backdrop = ctx.doc.createElement("div");
  backdrop.className = "modal-backdrop custom-modal-backdrop fade show";
  ctx.doc.body.appendChild(backdrop);
  ctx.fallbackBackdrop = backdrop;
  return backdrop;
};

const showEditModal = (ctx) => {
  if (!ctx.editModal) return;
  if (ctx.editBtn && ctx.titleInput) {
    ctx.titleInput.value = ctx.editBtn.getAttribute("data-collection-title") || "";
  }
  if (ctx.hasBootstrapModal) {
    ctx.editModalInstance = ctx.w.bootstrap.Modal.getOrCreateInstance(ctx.editModal);
    ctx.editModalInstance.show();
    return;
  }
  ensureFallbackBackdrop(ctx);
  ctx.editModal.classList.add("show");
  ctx.editModal.style.display = "block";
  ctx.editModal.removeAttribute("aria-hidden");
  ctx.doc.body.classList.add("modal-open");
};

const hideEditModal = (ctx) => {
  if (!ctx.editModal) return;
  if (ctx.hasBootstrapModal && ctx.editModalInstance) {
    ctx.editModalInstance.hide();
    return;
  }
  if (ctx.fallbackBackdrop) {
    ctx.fallbackBackdrop.remove();
    ctx.fallbackBackdrop = null;
  }
  ctx.editModal.classList.remove("show");
  ctx.editModal.style.display = "none";
  ctx.editModal.setAttribute("aria-hidden", "true");
  ctx.doc.body.classList.remove("modal-open");
};

const updateTitles = (ctx, title) => {
  ctx.doc.querySelectorAll(".collection-title").forEach((el) => {
    el.textContent = title;
  });
  if (ctx.editBtn) ctx.editBtn.setAttribute("data-collection-title", title);
};

const submitEdit = (ctx, newTitle) => {
  const body = new ctx.w.URLSearchParams({ name: newTitle, title: newTitle }).toString();
  return ctx.w
    .fetch(ctx.editEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": ctx.csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      body,
    })
    .then((resp) => (resp.ok ? resp.json().catch(() => null) : null));
};

const wireEditHandlers = (ctx) => {
  if (!ctx.editBtn || !ctx.editForm || !ctx.titleInput) return;
  ctx.editBtn.addEventListener("click", (event) => {
    event.preventDefault();
    showEditModal(ctx);
  });
  ctx.editForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const newTitle = (ctx.titleInput.value || "").trim();
    if (!newTitle) {
      ctx.titleInput.focus();
      return;
    }
    submitEdit(ctx, newTitle)
      .then((data) => updateTitles(ctx, (data && data.title) || newTitle))
      .catch(() => null)
      .finally(() => hideEditModal(ctx));
  });
};

const wireCloseHandlers = (ctx) => {
  if (ctx.closeBtn) {
    ctx.closeBtn.addEventListener("click", (event) => {
      event.preventDefault();
      hideEditModal(ctx);
    });
  }
  if (ctx.editModal) {
    ctx.editModal.addEventListener("click", (event) => {
      if (event.target === ctx.editModal) hideEditModal(ctx);
    });
  }
};

const submitDelete = (ctx) => {
  const body = new ctx.w.URLSearchParams({ id: ctx.collectionId }).toString();
  return ctx.w.fetch(ctx.deleteEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": ctx.csrfToken,
      "X-Requested-With": "XMLHttpRequest",
    },
    body,
  });
};

const wireDeleteHandler = (ctx) => {
  if (!ctx.deleteBtn) return;
  ctx.deleteBtn.addEventListener("click", (event) => {
    event.preventDefault();
    if (!ctx.w.confirm("Delete this collection? This cannot be undone.")) return;
    submitDelete(ctx)
      .catch(() => null)
      .finally(() => {
        ctx.w.location.href = ctx.redirectUrl;
      });
  });
};

const initCollectionDetail = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || w.__collectionDetailInitialized) return;
  w.__collectionDetailInitialized = true;
  const ctx = buildCtx(w);
  wireEditHandlers(ctx);
  wireCloseHandlers(ctx);
  wireDeleteHandler(ctx);
};

const autoInit = () => {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initCollectionDetail(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initCollectionDetail };
}

/* istanbul ignore next */
autoInit();
}
