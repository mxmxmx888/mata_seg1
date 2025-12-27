const VIEWS = { list: "list", create: "create" };
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const buildBackdrop = (doc) => {
  const el = doc.createElement("div");
  el.className = "modal-backdrop fade custom-modal-backdrop";
  doc.body.appendChild(el);
  return el;
};

const lockBody = (doc, locked) => {
  doc.body.classList.toggle("modal-open", locked);
  doc.body.style.overflow = locked ? "hidden" : "";
};

const createFallbackModalDisplay = (w, doc) => {
  let backdrop = null;
  const ensureBackdrop = () => (backdrop ? backdrop : (backdrop = buildBackdrop(doc)));
  const hide = (modal) => {
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    if (backdrop) {
      backdrop.classList.remove("show");
      backdrop.style.display = "none";
      backdrop.onclick = null;
    }
    lockBody(doc, false);
  };
  const show = (modal, onBackdrop) => {
    const el = ensureBackdrop();
    el.style.display = "block";
    w.requestAnimationFrame(() => el.classList.add("show"));
    modal.classList.add("show");
    modal.style.display = "block";
    modal.removeAttribute("aria-hidden");
    lockBody(doc, true);
    el.onclick = onBackdrop;
  };
  return { show, hide };
};

const buildSaveState = (w, doc) => {
  const modal = doc.getElementById("saveModal");
  if (!modal) return null;
  const csrfInput = doc.querySelector("input[name=csrfmiddlewaretoken]");
  return {
    w,
    doc,
    modal,
    views: Array.from(modal.querySelectorAll(".save-modal-view")),
    list: modal.querySelector(".save-modal-list"),
    searchInput: modal.querySelector(".save-modal-search input"),
    openCreate: modal.querySelector("[data-save-open-create]"),
    backBtn: modal.querySelector("[data-save-back]"),
    createForm: doc.getElementById("save-modal-create-form"),
    nameInput: doc.getElementById("new-collection-name"),
    hasBootstrap: !!(w.bootstrap && w.bootstrap.Modal),
    toggleButtons: Array.from(modal.querySelectorAll("[data-save-toggle]")),
    csrfToken: modal.dataset.csrf || (csrfInput ? csrfInput.value : ""),
    saveEndpoint: modal.dataset.saveEndpoint || "",
    fallback: createFallbackModalDisplay(w, doc),
    noResultsRow: null
  };
};

const getSaveRows = (state) => (state.list ? Array.from(state.list.querySelectorAll(".save-modal-row")) : []);

const ensureNoResultsRow = (state) => {
  if (state.noResultsRow || !state.list) return state.noResultsRow;
  const existing = state.list.querySelector(".save-modal-no-results");
  if (existing) {
    state.noResultsRow = existing;
    return existing;
  }
  const row = state.doc.createElement("li");
  row.className = "text-muted small px-1 py-2 save-modal-no-results d-none";
  row.textContent = "No collections found";
  state.list.appendChild(row);
  state.noResultsRow = row;
  return row;
};

const setRowSearchValue = (row, name) => {
  row.setAttribute("data-collection-name", (name || "").toLowerCase());
};

const prepareSearchState = (state) => {
  getSaveRows(state).forEach((row) => {
    const nameEl = row.querySelector(".fw-semibold");
    setRowSearchValue(row, nameEl ? nameEl.textContent : "");
  });
};

const filterSaveList = (state) => {
  if (!state.list || !state.searchInput) return;
  const rows = getSaveRows(state);
  if (!rows.length) return;
  const term = state.searchInput.value.trim().toLowerCase();
  let visible = 0;
  rows.forEach((row) => {
    const name = row.getAttribute("data-collection-name") || "";
    const match = !term || name.indexOf(term) !== -1;
    row.classList.toggle("d-none", !match);
    if (match) visible += 1;
  });
  const noResults = ensureNoResultsRow(state);
  if (noResults) noResults.classList.toggle("d-none", visible !== 0);
};

const resetSearch = (state) => {
  if (!state.searchInput) return;
  state.searchInput.value = "";
  filterSaveList(state);
};

const setSaveView = (state, view) => {
  if (!state.views.length) return;
  state.views.forEach((v) => {
    v.classList.toggle("d-none", v.getAttribute("data-save-view") !== view);
  });
  state.modal.querySelectorAll("[data-save-title]").forEach((title) => {
    title.classList.toggle("d-none", title.getAttribute("data-save-title") !== view);
  });
  state.modal.querySelectorAll("[data-save-subtitle]").forEach((subtitle) => {
    subtitle.classList.toggle("d-none", subtitle.getAttribute("data-save-subtitle") !== view);
  });
  state.modal.querySelectorAll("[data-hide-when-view]").forEach((el) => {
    el.classList.toggle("d-none", el.getAttribute("data-hide-when-view") === view);
  });
};

const showSaveModal = (state) => {
  setSaveView(state, VIEWS.list);
  resetSearch(state);
  if (state.hasBootstrap) {
    state.w.bootstrap.Modal.getOrCreateInstance(state.modal).show();
    return;
  }
  state.fallback.show(state.modal, () => hideSaveModal(state));
};

const hideSaveModal = (state) => {
  if (state.hasBootstrap) {
    state.w.bootstrap.Modal.getOrCreateInstance(state.modal).hide();
    return;
  }
  state.fallback.hide(state.modal);
};

const toggleIcon = (icon, saved) => {
  icon.classList.toggle("bi-bookmark-fill", saved);
  icon.classList.toggle("bi-bookmark", !saved);
};

const fetchToggleSave = (state, collectionId) => {
  const body = new URLSearchParams({ collection_id: collectionId }).toString();
  return state.w.fetch(state.saveEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": state.csrfToken,
      "X-Requested-With": "XMLHttpRequest"
    },
    body
  });
};

const handleToggleRequest = (state, btn) => {
  const collectionId = btn.getAttribute("data-collection-id");
  const icon = btn.querySelector("i");
  if (!collectionId || !icon) return null;
  return fetchToggleSave(state, collectionId)
    .then((resp) => (resp && resp.ok ? resp.json().catch(() => null) : null))
    .then((data) => {
      const saved = data && Object.prototype.hasOwnProperty.call(data, "saved")
        ? !!data.saved
        : !icon.classList.contains("bi-bookmark-fill");
      toggleIcon(icon, saved);
    })
    .catch(() => {
      const saved = !icon.classList.contains("bi-bookmark-fill");
      toggleIcon(icon, saved);
    });
};

const attachToggleHandler = (state, btn) => {
  if (!btn || btn.dataset.saveHandlerAttached === "1") return;
  btn.dataset.saveHandlerAttached = "1";
  const row = btn.closest(".save-modal-row");
  const handleToggle = (event) => {
    event.preventDefault();
    handleToggleRequest(state, btn);
  };
  btn.addEventListener("click", handleToggle);
  if (row) {
    row.addEventListener("click", (event) => {
      if (event.target.closest("[data-save-toggle]")) return;
      handleToggle(event);
    });
  }
};

const makeRowElement = (state, collection) => {
  const row = state.doc.createElement("li");
  row.className = "save-modal-row";
  row.setAttribute("data-collection-id", collection.id);
  row.innerHTML = `
    <div class="save-modal-avatar${collection.thumb_url ? " save-modal-avatar-has-thumb" : ""}" aria-hidden="true">
      ${collection.thumb_url ? `<img src="${collection.thumb_url}" alt="" class="save-modal-avatar-img">` : (collection.name || "").charAt(0).toUpperCase()}
    </div>
    <div>
      <p class="mb-0 fw-semibold"></p>
      <p class="mb-0 text-muted small">Private</p>
    </div>
    <button
      type="button"
      class="save-modal-action"
      data-save-toggle
      data-collection-id="${collection.id}"
      aria-label="Toggle ${collection.name || ""}"
    >
      <i class="bi"></i>
    </button>
  `;
  return row;
};

const applyRowState = (state, row, collection, saved) => {
  const nameEl = row.querySelector("p.mb-0.fw-semibold") || row.querySelector("p.fw-semibold");
  if (nameEl) {
    nameEl.textContent = collection.name || "";
    setRowSearchValue(row, collection.name || "");
  }
  const toggleBtn = row.querySelector("[data-save-toggle]");
  const icon = toggleBtn ? toggleBtn.querySelector("i") : null;
  if (icon) {
    toggleIcon(icon, saved);
  }
  attachToggleHandler(state, toggleBtn);
};

const buildNewRow = (state, collection, saved) => {
  const row = makeRowElement(state, collection);
  if (state.list) state.list.appendChild(row);
  applyRowState(state, row, collection, saved);
  return row;
};

const createCollection = (state, name) => {
  const body = new URLSearchParams({ collection_name: name }).toString();
  return state.w.fetch(state.saveEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": state.csrfToken,
      "X-Requested-With": "XMLHttpRequest"
    },
    body
  });
};

const upsertCollectionRow = (state, data) => {
  if (!data || !data.collection) return;
  const saved = !!data.saved;
  const existing = state.list
    ? state.list.querySelector(`[data-collection-id="${data.collection.id}"]`)
    : null;
  const row = existing || buildNewRow(state, data.collection, saved);
  if (existing) {
    const toggleBtn = row.querySelector("[data-save-toggle]");
    if (toggleBtn) attachToggleHandler(state, toggleBtn);
  }
  filterSaveList(state);
  setSaveView(state, VIEWS.list);
  hideSaveModal(state);
};

const handleCreateSubmit = (state) => {
  if (!state.createForm) return;
  state.createForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = (state.nameInput?.value || "").trim();
    if (!name) {
      if (state.nameInput) state.nameInput.focus();
      return;
    }
    createCollection(state, name)
      .then((resp) => (resp && resp.ok ? resp.json().catch(() => null) : null))
      .then((data) => upsertCollectionRow(state, data))
      .catch(() => hideSaveModal(state));
  });
};

const wireViewButtons = (state) => {
  if (state.openCreate) {
    state.openCreate.addEventListener("click", (event) => {
      event.preventDefault();
      setSaveView(state, VIEWS.create);
      if (state.nameInput) state.nameInput.focus();
    });
  }
  if (state.backBtn) {
    state.backBtn.addEventListener("click", (event) => {
      event.preventDefault();
      setSaveView(state, VIEWS.list);
    });
  }
};

const wireModalTriggers = (state) => {
  Array.from(state.doc.querySelectorAll("[data-open-save-modal]")).forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      showSaveModal(state);
    });
  });
  state.modal.querySelectorAll("[data-dismiss-save-modal]").forEach((btn) => {
    btn.addEventListener("click", () => hideSaveModal(state));
  });
  state.modal.addEventListener("click", (event) => {
    if (!state.modal.classList.contains("show")) return;
    const dialog = state.modal.querySelector(".modal-dialog");
    if (dialog && dialog.contains(event.target)) return;
    hideSaveModal(state);
  });
  if (state.hasBootstrap) {
    state.modal.addEventListener("shown.bs.modal", () => setSaveView(state, VIEWS.list));
  }
};

const initSaveModal = (win) => {
  const w = resolveWindow(win);
  if (!w) return;
  const state = buildSaveState(w, w.document);
  if (!state) return;
  if (state.modal.dataset.saveModalInitialized === "1") return;
  state.modal.dataset.saveModalInitialized = "1";
  prepareSearchState(state);
  if (state.searchInput) {
    state.searchInput.addEventListener("input", () => filterSaveList(state));
  }
  wireViewButtons(state);
  wireModalTriggers(state);
  handleCreateSubmit(state);
  state.toggleButtons.forEach((btn) => attachToggleHandler(state, btn));
  filterSaveList(state);
};

const autoInitSaveModal = () => {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initSaveModal(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initSaveModal };
}

/* istanbul ignore next */
autoInitSaveModal();
