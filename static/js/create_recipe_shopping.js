(function (global) {
  const MAX_SHOPPING_LINKS = 10;

  function createState(params) {
    return {
      ...params,
      shoppingList: [],
      shopImageFiles: [],
      previewUrl: null,
      pendingFile: null,
      pendingPreviewUrl: null,
      existingShoppingItems: params.existingShoppingItems || [],
    };
  }

  function safeNormalize(normalizeFn, url) {
    return typeof normalizeFn === "function" ? normalizeFn(url) : url;
  }

  function setShoppingField(state) {
    if (!state.shoppingField) return;
    state.shoppingField.value = state.shoppingList
      .map((item) => (item.url ? `${item.name} | ${item.url}` : item.name))
      .join("\n");
  }

  function revokeUrl(state, url) {
    if (!url || !state.w.URL || typeof state.w.URL.revokeObjectURL !== "function") return;
    try {
      state.w.URL.revokeObjectURL(url);
    } catch (err) {
      /* istanbul ignore next */
    }
  }

  function clearPreview(state) {
    revokeUrl(state, state.previewUrl);
    state.previewUrl = null;
  }

  function createObjectUrl(state, file) {
    if (!file || !state.w.URL || typeof state.w.URL.createObjectURL !== "function") return null;
    return state.w.URL.createObjectURL(file);
  }

  function buildPreviewHtml(file, url) {
    const img = url ? `<img src="${url}" alt="${file.name}" class="image-thumb">` : "";
    return `
      <span class="image-preview-item" data-idx="0">
        ${img}
        <span class="image-preview-name">${file.name}</span>
        <button type="button" class="image-remove" data-idx="0" aria-label="Remove ${file.name}">&times;</button>
      </span>
    `;
  }

  function renderShopImagesList(state) {
    if (!state.shopImageList) return;
    const hasPending = !!state.pendingFile;
    if (!hasPending) {
      const uploadedNames = state.shopImageFiles.filter(Boolean).map((f) => f.name).filter(Boolean);
      revokeUrl(state, state.pendingPreviewUrl);
      state.pendingPreviewUrl = null;
      state.shopImageList.textContent = uploadedNames.join(", ");
      return;
    }
    revokeUrl(state, state.pendingPreviewUrl);
    const url = createObjectUrl(state, state.pendingFile);
    state.pendingPreviewUrl = url;
    state.shopImageList.innerHTML = buildPreviewHtml(state.pendingFile, url);
    const removeBtn = state.shopImageList.querySelector(".image-remove");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        state.pendingFile = null;
        revokeUrl(state, state.pendingPreviewUrl);
        state.pendingPreviewUrl = null;
        renderShopImagesList(state);
      });
    }
  }

  function toFileList(state) {
    if (typeof state.w.DataTransfer === "undefined") return state.shopImageFiles;
    const dt = new state.w.DataTransfer();
    state.shopImageFiles.forEach((f) => f && dt.items.add(f));
    return dt.files;
  }

  function syncShopImagesInput(state) {
    if (!state.shopImageInput || typeof state.setInputFiles !== "function") return;
    state.setInputFiles(state.shopImageInput, toFileList(state));
    renderShopImagesList(state);
  }

  function showShoppingError(doc, field, message) {
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
  }

  function clearShoppingError(field) {
    if (!field) return;
    const container =
      field.closest(".shopping-links-field") || field.closest(".shopping-links-upload") || field.parentElement;
    if (!container) return;
    container.querySelectorAll(".client-required-error").forEach((el) => el.remove());
  }

  function buildListHtml(list) {
    return list
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
  }

  function removeItem(state, idx) {
    const removed = state.shoppingList.splice(idx, 1)[0];
    const removedFile = state.shopImageFiles.splice(idx, 1)[0];
    if (removed && removed.previewUrl) revokeUrl(state, removed.previewUrl);
    if (removedFile && removedFile.previewUrl) revokeUrl(state, removedFile.previewUrl);
    clearShoppingError(state.itemInput);
    syncShopImagesInput(state);
    renderList(state);
  }

  function attachRemoveHandlers(state) {
    state.listBox.querySelectorAll(".remove").forEach((btn) => {
      btn.addEventListener("click", () => removeItem(state, parseInt(btn.dataset.idx, 10)));
    });
  }

  function renderList(state) {
    if (!state.listBox) return;
    if (!state.shoppingList.length) {
      state.listBox.innerHTML = '<div class="text-secondary small fst-italic">No shopping links added yet.</div>';
      setShoppingField(state);
      return;
    }
    state.listBox.innerHTML = buildListHtml(state.shoppingList);
    attachRemoveHandlers(state);
    setShoppingField(state);
  }

  function parseFiles(state) {
    const inputFiles =
      state.shopImageInput && typeof state.getFiles === "function"
        ? Array.from(state.getFiles(state.shopImageInput) || [])
        : [];

    if (!inputFiles.length) {
      if (state.pendingFile) {
        revokeUrl(state, state.pendingPreviewUrl);
        state.pendingPreviewUrl = null;
      }
      state.pendingFile = null;
      return [];
    }

    if (state.pendingFile) return [state.pendingFile];

    const storedCount = state.shopImageFiles.filter(Boolean).length;
    if (storedCount === 0 || inputFiles.length > storedCount) {
      state.pendingFile = inputFiles[0];
      return inputFiles;
    }
    return [];
  }

  function hasMissingFields(state, name, rawUrl, files) {
    let missing = false;
    clearShoppingError(state.itemInput);
    clearShoppingError(state.linkInput);
    clearShoppingError(state.shopImageInput);
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
  }

  function focusFirstMissing(state, name, rawUrl, files) {
    if (!name) {
      state.itemInput.focus();
    } else if (!rawUrl) {
      state.linkInput.focus();
    } else if (!files.length && state.shopImageInput) {
      state.shopImageInput.focus();
    }
  }

  function resetInputs(state) {
    state.itemInput.value = "";
    state.linkInput.value = "";
    if (state.shopImageInput) {
      state.shopImageInput.value = "";
      renderShopImagesList(state);
    }
    state.itemInput.focus();
  }

  function addLink(state) {
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
    const file = files[0];
    const previewUrl = createObjectUrl(state, file);
    state.shoppingList.push({ name, url: safeNormalize(state.normalizeUrl, rawUrl), previewUrl });
    state.shopImageFiles.push(file);
    state.pendingFile = null;
    revokeUrl(state, state.pendingPreviewUrl);
    state.pendingPreviewUrl = null;
    syncShopImagesInput(state);
    renderList(state);
    resetInputs(state);
  }

  function bootstrapExisting(state) {
    const rawShopping = (state.shoppingField.value || "").trim();
    const existingByKey = {};
    (state.existingShoppingItems || []).forEach((item) => {
      const key = `${(item.name || "").trim().toLowerCase()}|${(item.url || "").trim().toLowerCase()}`;
      existingByKey[key] = item;
    });

    const lines = rawShopping
      ? rawShopping.split(/\r?\n/).filter((line) => line && line.trim())
      : [];

    const sourceItems =
      lines.length > 0
        ? lines.map((line) => {
            const parts = line.split("|");
            return {
              name: (parts[0] || "").trim(),
              rawUrl: (parts[1] || "").trim(),
            };
          })
        : (state.existingShoppingItems || []).map((item) => ({
            name: (item.name || "").trim(),
            rawUrl: (item.url || "").trim(),
          }));

    sourceItems.forEach((item) => {
      if (!item || !item.name) return;
      const url = safeNormalize(state.normalizeUrl, item.rawUrl);
      const key = `${item.name.toLowerCase()}|${(item.rawUrl || url || "").trim().toLowerCase()}`;
      const existing = existingByKey[key] || {};
      const previewUrl = existing.image_url || null;
      if (state.shoppingList.length >= MAX_SHOPPING_LINKS) return;
      state.shoppingList.push({ name: item.name, url, previewUrl });
      state.shopImageFiles.push(null);
    });
  }

  function bindEnter(el, handler) {
    if (!el) return;
    el.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handler();
      }
    });
  }

  function bindFieldClear(el) {
    if (!el) return;
    el.addEventListener("input", () => clearShoppingError(el));
    el.addEventListener("change", () => clearShoppingError(el));
  }

  function bindShopImageInput(state) {
    if (!state.shopImageInput) return;
    state.shopImageInput.multiple = false;
    state.shopImageInput.addEventListener("change", () => {
      const files = typeof state.getFiles === "function" ? state.getFiles(state.shopImageInput) : [];
      const asArray = files ? Array.from(files) : [];
      state.pendingFile = asArray.length ? asArray[0] : null;
      renderShopImagesList(state);
    });
  }

  function bind(state) {
    [state.itemInput, state.linkInput, state.shopImageInput].forEach(bindFieldClear);
    state.addBtn.addEventListener("click", () => addLink(state));
    bindEnter(state.itemInput, () => addLink(state));
    bindEnter(state.linkInput, () => addLink(state));
    bindShopImageInput(state);
  }

  function createShoppingManager(params) {
    const state = createState(params);
    return {
      addLink: () => addLink(state),
      bind: () => bind(state),
      bootstrapExisting: () => bootstrapExisting(state),
      renderList: () => renderList(state),
      syncShoppingField: () => setShoppingField(state),
      syncShopImagesInput: () => syncShopImagesInput(state),
    };
  }

  const api = { createShoppingManager };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  /* istanbul ignore next */
  if (global) {
    global.createRecipeShopping = api;
  }
})(typeof window !== "undefined" ? window : null);
