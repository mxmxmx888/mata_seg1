{
const MAX_SHOPPING_LINKS = 10;
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => win || globalWindow || (typeof window !== "undefined" ? window : null);

const createState = (params) => ({
  ...params,
  w: resolveWindow(params.w),
  shoppingList: [],
  shopImageFiles: [],
  pendingFile: null,
  pendingPreviewUrl: null,
  existingShoppingItems: params.existingShoppingItems || [],
});

const safeNormalize = (normalizeFn, url) => (typeof normalizeFn === "function" ? normalizeFn(url) : url);

const setShoppingField = (state) => {
  if (!state.shoppingField) return;
  state.shoppingField.value = state.shoppingList
    .map((item) => (item.url ? `${item.name} | ${item.url}` : item.name))
    .join("\n");
};

const revokeUrl = (state, url) => {
  if (!url || !state.w || !state.w.URL || typeof state.w.URL.revokeObjectURL !== "function") return;
  try {
    state.w.URL.revokeObjectURL(url);
  } catch (err) {
    /* ignore */
  }
};

const createObjectUrl = (state, file) => {
  if (!file || !state.w || !state.w.URL || typeof state.w.URL.createObjectURL !== "function") return null;
  return state.w.URL.createObjectURL(file);
};

const buildPreviewHtml = (file, url) => {
  const img = url ? `<img src="${url}" alt="${file.name}" class="image-thumb">` : "";
  return `
    <span class="image-preview-item" data-idx="0">
      ${img}
      <span class="image-preview-name">${file.name}</span>
      <button type="button" class="image-remove" data-idx="0" aria-label="Remove ${file.name}">&times;</button>
    </span>
  `;
};

const clearPendingPreview = (state) => {
  revokeUrl(state, state.pendingPreviewUrl);
  state.pendingPreviewUrl = null;
};

const clearPendingFile = (state) => {
  clearPendingPreview(state);
  state.pendingFile = null;
};

const renderShopImagesList = (state) => {
  if (!state.shopImageList) return;
  if (state.pendingFile) {
    clearPendingPreview(state);
    const url = createObjectUrl(state, state.pendingFile);
    state.pendingPreviewUrl = url;
    state.shopImageList.innerHTML = buildPreviewHtml(state.pendingFile, url);
    const removeBtn = state.shopImageList.querySelector(".image-remove");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        clearPendingFile(state);
        renderShopImagesList(state);
      });
    }
    return;
  }
  clearPendingPreview(state);
  const names = state.shopImageFiles.filter(Boolean).map((file) => file.name).filter(Boolean);
  state.shopImageList.textContent = names.length ? names.join(", ") : "";
};

const toFileList = (state) => {
  if (!state.w || typeof state.w.DataTransfer === "undefined") return state.shopImageFiles;
  const dt = new state.w.DataTransfer();
  state.shopImageFiles.forEach((f) => f && dt.items.add(f));
  return dt.files;
};

const syncShopImagesInput = (state) => {
  if (!state.shopImageInput || typeof state.setInputFiles !== "function") return;
  state.setInputFiles(state.shopImageInput, toFileList(state));
  renderShopImagesList(state);
};

const showShoppingError = (doc, field, message) => {
  if (!field) return;
  const container =
    field.closest(".shopping-links-field") || field.closest(".shopping-links-upload") || field.parentElement;
  if (!container) return;
  let msg = container.querySelector(".client-required-error");
  if (!msg) {
    msg = doc.createElement("div");
    msg.className = "client-required-error";
    container.appendChild(msg);
  }
  msg.textContent = message;
};

const clearShoppingError = (field) => {
  if (!field) return;
  const container =
    field.closest(".shopping-links-field") || field.closest(".shopping-links-upload") || field.parentElement;
  if (!container) return;
  container.querySelectorAll(".client-required-error").forEach((el) => el.remove());
};

const buildListHtml = (list) =>
  list
    .map(
      (item, idx) => `
      <div class="shopping-list-item" data-idx="${idx}">
        <div class="d-flex align-items-center gap-2">
          ${item.previewUrl ? `<img src="${item.previewUrl}" alt="${item.name}" class="shopping-thumb">` : ""}
          <span class="fw-medium">${item.name}</span>
          <span class="note">${item.url ? '<i class="bi bi-link-45deg"></i> Linked' : ""}</span>
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger remove py-0 px-2" data-idx="${idx}">Remove</button>
      </div>
    `
    )
    .join("");

const removeItem = (state, idx) => {
  const removed = state.shoppingList.splice(idx, 1)[0];
  const removedFile = state.shopImageFiles.splice(idx, 1)[0];
  if (removed && removed.previewUrl) revokeUrl(state, removed.previewUrl);
  if (removedFile && removedFile.previewUrl) revokeUrl(state, removedFile.previewUrl);
  clearShoppingError(state.itemInput);
  syncShopImagesInput(state);
  renderList(state);
};

const attachRemoveHandlers = (state) => {
  state.listBox.querySelectorAll(".remove").forEach((btn) => {
    btn.addEventListener("click", () => removeItem(state, parseInt(btn.dataset.idx, 10)));
  });
};

const renderList = (state) => {
  if (!state.listBox) return;
  if (!state.shoppingList.length) {
    state.listBox.innerHTML = '<div class="text-secondary small fst-italic">No shopping links added yet.</div>';
    setShoppingField(state);
    return;
  }
  state.listBox.innerHTML = buildListHtml(state.shoppingList);
  attachRemoveHandlers(state);
  setShoppingField(state);
};

const clearAllErrors = (state) => {
  clearShoppingError(state.itemInput);
  clearShoppingError(state.linkInput);
  clearShoppingError(state.shopImageInput);
};

const getInputFiles = (state) => {
  if (!state.shopImageInput || typeof state.getFiles !== "function") return [];
  const files = state.getFiles(state.shopImageInput);
  return files ? Array.from(files) : [];
};

const choosePendingFile = (state, inputFiles, storedFiles) => {
  if (state.pendingFile) return state.pendingFile;
  const newSelection = inputFiles.find((file) => !storedFiles.includes(file));
  if (newSelection) return newSelection;
  if (storedFiles.length === 0 || inputFiles.length > storedFiles.length) return inputFiles[0];
  return null;
};

const parseFiles = (state) => {
  const inputFiles = getInputFiles(state);
  const storedFiles = state.shopImageFiles.filter(Boolean);
  if (!inputFiles.length) {
    clearPendingFile(state);
    return [];
  }
  const picked = choosePendingFile(state, inputFiles, storedFiles);
  if (picked) state.pendingFile = picked;
  return state.pendingFile ? [state.pendingFile] : [];
};

const hasMissingFields = (state, name, rawUrl, files) => {
  let missing = false;
  clearAllErrors(state);
  if (!name) {
    showShoppingError(state.doc, state.itemInput, "Please add an item name.");
    missing = true;
  }
  if (!rawUrl) {
    showShoppingError(state.doc, state.linkInput, "Please add an online link.");
    missing = true;
  }
  if (!files.length) {
    showShoppingError(state.doc, state.shopImageInput, "Please choose an image for this item.");
    missing = true;
  }
  return missing;
};

const focusFirstMissing = (state, name, rawUrl, files) => {
  if (!name) {
    state.itemInput.focus();
    return;
  }
  if (!rawUrl) {
    state.linkInput.focus();
    return;
  }
  if (!files.length && state.shopImageInput) {
    state.shopImageInput.focus();
  }
};

const resetInputs = (state) => {
  state.itemInput.value = "";
  state.linkInput.value = "";
  if (state.shopImageInput) {
    state.shopImageInput.value = "";
    renderShopImagesList(state);
  }
  state.itemInput.focus();
};

const pushShoppingItem = (state, name, rawUrl, file) => {
  const previewUrl = createObjectUrl(state, file);
  state.shoppingList.push({ name, url: safeNormalize(state.normalizeUrl, rawUrl), previewUrl });
  state.shopImageFiles.push(file);
};

const finalizeAddition = (state) => {
  state.pendingFile = null;
  clearPendingPreview(state);
  syncShopImagesInput(state);
  renderList(state);
  resetInputs(state);
};

const addLink = (state) => {
  clearShoppingError(state.itemInput);
  if (state.shoppingList.length >= MAX_SHOPPING_LINKS) {
    showShoppingError(state.doc, state.itemInput, `You can add up to ${MAX_SHOPPING_LINKS} shopping links.`);
    state.itemInput.focus();
    return;
  }
  const name = (state.itemInput.value || "").trim();
  const rawUrl = (state.linkInput.value || "").trim();
  const files = parseFiles(state);
  if (hasMissingFields(state, name, rawUrl, files)) {
    focusFirstMissing(state, name, rawUrl, files);
    return;
  }
  pushShoppingItem(state, name, rawUrl, files[0]);
  finalizeAddition(state);
};

const parseLinesFromField = (state) => {
  const rawShopping = (state.shoppingField.value || "").trim();
  if (!rawShopping) return [];
  return rawShopping
    .split(/\r?\n/)
    .filter((line) => line && line.trim())
    .map((line) => {
      const parts = line.split("|");
      return { name: (parts[0] || "").trim(), rawUrl: (parts[1] || "").trim() };
    });
};

const normalizeExistingItems = (existing = []) =>
  existing.map((item) => ({
    name: (item.name || "").trim(),
    rawUrl: (item.url || "").trim(),
    previewUrl: item.image_url || null,
  }));

const bootstrapExisting = (state) => {
  const lines = parseLinesFromField(state);
  const sourceItems = lines.length ? lines : normalizeExistingItems(state.existingShoppingItems);
  sourceItems.forEach((item) => {
    if (!item || !item.name || state.shoppingList.length >= MAX_SHOPPING_LINKS) return;
    const url = safeNormalize(state.normalizeUrl, item.rawUrl);
    state.shoppingList.push({ name: item.name, url, previewUrl: item.previewUrl || null });
    state.shopImageFiles.push(null);
  });
};

const bindEnter = (el, handler) => {
  if (!el) return;
  el.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handler();
    }
  });
};

const bindFieldClear = (el) => {
  if (!el) return;
  el.addEventListener("input", () => clearShoppingError(el));
  el.addEventListener("change", () => clearShoppingError(el));
};

const bindShopImageInput = (state) => {
  if (!state.shopImageInput) return;
  state.shopImageInput.multiple = false;
  state.shopImageInput.addEventListener("change", () => {
    const files = getInputFiles(state);
    state.pendingFile = files.length ? files[0] : null;
    renderShopImagesList(state);
  });
};

const bind = (state) => {
  [state.itemInput, state.linkInput, state.shopImageInput].forEach(bindFieldClear);
  state.addBtn.addEventListener("click", () => addLink(state));
  bindEnter(state.itemInput, () => addLink(state));
  bindEnter(state.linkInput, () => addLink(state));
  bindShopImageInput(state);
};

const createShoppingManager = (params) => {
  const state = createState(params);
  return {
    addLink: () => addLink(state),
    bind: () => bind(state),
    bootstrapExisting: () => bootstrapExisting(state),
    renderList: () => renderList(state),
    syncShoppingField: () => setShoppingField(state),
    syncShopImagesInput: () => syncShopImagesInput(state),
  };
};

const api = { createShoppingManager };

if (hasModuleExports) {
  module.exports = api;
}

/* istanbul ignore next */
if (globalWindow) {
  globalWindow.createRecipeShopping = api;
}
}
