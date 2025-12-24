(function (global) {
  function normalizeUrl(url) {
    if (!url) return "";
    return /^https?:\/\//i.test(url) ? url : "https://" + url;
  }

  function setInputFiles(input, files) {
    /* istanbul ignore next */
    if (!input || !files) return;
    input.__mockFiles = files;
    try {
      Object.defineProperty(input, "files", {
        configurable: true,
        get: () => files
      });
    } catch (err) {
      // Silent fallback: if defining files fails, ignore.
    }
  }

  function getFiles(input) {
    /* istanbul ignore next */
    if (!input) return null;
    const real = input.files;
    if (real && real.length) return real;
    return input.__mockFiles || real;
  }

  function initCreateRecipe(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    /* istanbul ignore next */
    if (!w || !w.document) return;
    const doc = w.document;

    const formEl = doc.querySelector(".create-recipe-card form");
    const imageInput = doc.getElementById("id_images");
    const imageList = doc.getElementById("image-file-list");
    const shopImageInput = doc.getElementById("id_shop_images");
    const shopImageList = doc.getElementById("shop-image-file-list");
    const shoppingField = doc.getElementById("id_shopping_links_text");
    const isBound = formEl && formEl.dataset.formBound === "true";
    const hasErrors = formEl && formEl.dataset.formHasErrors === "true";
    const requiredFields = formEl ? Array.from(formEl.querySelectorAll("[required]")) : [];
    const IMG_STORAGE_KEY = "create-recipe-images";
    const ingredientsField = doc.getElementById("id_ingredients_text");
    const itemInput = doc.getElementById("shop-item");
    const linkInput = doc.getElementById("shop-link");
    const addBtn = doc.getElementById("add-shop-link");
    const listBox = doc.getElementById("shop-list");
    const shoppingList = [];
    const shopImageFiles = [];

    /* istanbul ignore next */
    if (!formEl || !ingredientsField || !itemInput || !linkInput || !addBtn || !listBox || !shoppingField) return;

    if (imageInput) {
      imageInput.setAttribute("required", "required");
      requiredFields.push(imageInput);
    }

    function clearFieldError(field) {
      const container = field.closest(".mb-3") || field.parentElement;
      /* istanbul ignore next */
      if (!container) return;
      /* istanbul ignore next */
      container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
    }

    function renderRequiredFieldErrors() {
      let hasClientErrors = false;
      /* istanbul ignore next */
      formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
      requiredFields.forEach((field) => {
        const candidateFiles = field.type === "file" ? getFiles(field) : null;
        let isMissing = field.validity ? field.validity.valueMissing : !(field.value || "").trim();
        if (candidateFiles && candidateFiles.length) {
          isMissing = false;
        }
        if (!isMissing) {
          clearFieldError(field);
          return;
        }
        hasClientErrors = true;
        const message = doc.createElement("div");
        message.className = "client-required-error";
        message.textContent = "field required";
        const container = field.closest(".mb-3") || field.parentElement;
        const invalidFeedback = container ? container.querySelector(".invalid-feedback") : null;
        if (invalidFeedback) {
          invalidFeedback.insertAdjacentElement("beforebegin", message);
        } else if (container) {
          container.appendChild(message);
        } else {
          /* istanbul ignore next */
          field.insertAdjacentElement("afterend", message);
        }
      });
      return hasClientErrors;
    }

    requiredFields.forEach((field) => {
      /* istanbul ignore next */
      field.addEventListener("input", () => clearFieldError(field));
      /* istanbul ignore next */
      field.addEventListener("change", () => clearFieldError(field));
    });

    function renderImagesList() {
      /* istanbul ignore next */
      if (!imageInput || !imageList) return;
      const files = getFiles(imageInput);
      if (!files || !files.length) {
        imageList.textContent = "";
        return;
      }
      const names = Array.from(files).map((f) => f.name);
      imageList.textContent = names.join(", ");
    }
    if (imageInput) {
      imageInput.addEventListener("change", () => {
        renderImagesList();
        persistFiles(imageInput, IMG_STORAGE_KEY);
      });
    }

    function renderShopImagesList() {
      /* istanbul ignore next */
      if (!shopImageList) return;
      if (!shopImageFiles.length) {
        shopImageList.textContent = "";
        return;
      }
      const names = shopImageFiles.filter(Boolean).map((f) => f.name);
      shopImageList.textContent = names.join(", ");
    }
    if (shopImageInput) {
      shopImageInput.multiple = false;
      shopImageInput.addEventListener("change", renderShopImagesList);
    }

    function syncShopImagesInput() {
      /* istanbul ignore next */
      if (!shopImageInput || typeof w.DataTransfer === "undefined") return;
      const dt = new w.DataTransfer();
      shopImageFiles.forEach((f) => {
        if (f) dt.items.add(f);
      });
      setInputFiles(shopImageInput, dt.files);
      renderShopImagesList();
    }

    function syncShoppingField() {
      /* istanbul ignore next */
      if (!shoppingField) return;
      shoppingField.value = shoppingList
        .map((item) => (item.url ? `${item.name} | ${item.url}` : item.name))
        .join("\n");
    }

    function renderList() {
      if (!shoppingList.length) {
        listBox.innerHTML = '<div class="text-secondary small fst-italic">No shopping links added yet.</div>';
        syncShoppingField();
        return;
      }
      listBox.innerHTML = shoppingList
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
      listBox.querySelectorAll(".remove").forEach((btn) => {
        btn.addEventListener("click", () => {
          const i = parseInt(btn.dataset.idx, 10);
          const removed = shoppingList.splice(i, 1)[0];
          const removedFile = shopImageFiles.splice(i, 1)[0];
          if (removed && removed.previewUrl) w.URL.revokeObjectURL(removed.previewUrl);
          /* istanbul ignore next */
          if (removedFile && removedFile.previewUrl) w.URL.revokeObjectURL(removedFile.previewUrl);
          syncShopImagesInput();
          renderList();
        });
      });
      syncShoppingField();
    }

    function showShoppingError(field, message) {
      /* istanbul ignore next */
      if (!field) return;
      const container = field.closest(".shopping-links-field") || field.closest(".shopping-links-upload") || field.parentElement;
      /* istanbul ignore next */
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
      /* istanbul ignore next */
      if (!field) return;
      const container = field.closest(".shopping-links-field") || field.closest(".shopping-links-upload") || field.parentElement;
      /* istanbul ignore next */
      if (!container) return;
      container.querySelectorAll(".client-required-error").forEach((el) => el.remove());
    }

    [itemInput, linkInput, shopImageInput].forEach((el) => {
      /* istanbul ignore next */
      if (!el) return;
      /* istanbul ignore next */
      el.addEventListener("input", () => clearShoppingError(el));
      /* istanbul ignore next */
      el.addEventListener("change", () => clearShoppingError(el));
    });

    function addLink() {
      const name = (itemInput.value || "").trim();
      const rawUrl = (linkInput.value || "").trim();
      const files = getFiles(shopImageInput) ? Array.from(getFiles(shopImageInput)) : [];
      let hasMissing = false;

      clearShoppingError(itemInput);
      clearShoppingError(linkInput);
      clearShoppingError(shopImageInput);

      if (!name) {
        showShoppingError(itemInput, "Please add an item name.");
        hasMissing = true;
      }
      if (!rawUrl) {
        showShoppingError(linkInput, "Please add an online link.");
        hasMissing = true;
      }
      if (!files.length) {
        showShoppingError(shopImageInput, "Please choose an image for this item.");
        hasMissing = true;
      }
      if (hasMissing) {
        if (!name) itemInput.focus();
        else if (!rawUrl) linkInput.focus();
        else if (!files.length && shopImageInput) shopImageInput.focus();
        return;
      }

      const file = files[0];
      const previewUrl = w.URL.createObjectURL(file);
      shoppingList.push({ name, url: normalizeUrl(rawUrl), previewUrl });
      shopImageFiles.push(file);
      syncShopImagesInput();
      renderList();

      itemInput.value = "";
      linkInput.value = "";
      if (shopImageInput) {
        shopImageInput.value = "";
        renderShopImagesList();
      }
      itemInput.focus();
    }

    function cleanIngredientsField() {
      const manual = (ingredientsField.value || "").trim();
      const manualLines = manual ? manual.split(/\r?\n/).map((l) => l.trim()).filter(Boolean) : [];
      ingredientsField.value = manualLines.join("\n");
    }

    function persistFiles(input, storageKey) {
      /* istanbul ignore next */
      if (!input || !storageKey) return;
      const files = getFiles(input);
      if (!files || !files.length) {
        try {
          w.sessionStorage.removeItem(storageKey);
        } catch (err) {}
        return;
      }

      const entries = Array.from(files)
        .slice(0, 10)
        .map(
          (file) =>
            new Promise((resolve) => {
              const reader = new w.FileReader();
              reader.onload = () =>
                resolve({
                  name: file.name,
                  type: file.type,
                  lastModified: file.lastModified,
                  data: reader.result
                });
              reader.onerror = () => resolve(null);
              reader.readAsDataURL(file);
            })
        );

      Promise.all(entries).then((results) => {
        const cleaned = results.filter(Boolean);
        if (!cleaned.length) {
          try {
            w.sessionStorage.removeItem(storageKey);
          } catch (err) {}
          return;
        }
        try {
          w.sessionStorage.setItem(storageKey, JSON.stringify(cleaned));
        } catch (err) {}
      });
    }

    async function restoreFiles(input, storageKey, onAfterRestore) {
      /* istanbul ignore next */
      if (!input || !storageKey) return;
      /* istanbul ignore next */
      if (typeof w.DataTransfer === "undefined") return;
      let stored = [];
      try {
        stored = JSON.parse(w.sessionStorage.getItem(storageKey) || "[]");
      } catch (err) {
        /* istanbul ignore next */
        return;
      }
      /* istanbul ignore next */
      if (!Array.isArray(stored) || !stored.length) return;

      const dataTransfer = new w.DataTransfer();
      for (const item of stored) {
        /* istanbul ignore next */
        if (!item || !item.data) continue;
        try {
          const response = await w.fetch(item.data);
          const blob = await response.blob();
          const file = new w.File([blob], item.name || "upload", {
            type: item.type || blob.type || "application/octet-stream",
            lastModified: item.lastModified || Date.now()
          });
          dataTransfer.items.add(file);
        } catch (err) {
          /* istanbul ignore next */
          continue;
        }
      }

      if (dataTransfer.files.length) {
        setInputFiles(input, dataTransfer.files);
        if (typeof onAfterRestore === "function") onAfterRestore();
      }
    }

    function bootstrapExisting() {
      cleanIngredientsField();
      const rawShopping = (shoppingField.value || "").trim();
      if (!rawShopping) return;
      const lines = rawShopping.split(/\r?\n/);
      lines.forEach((line) => {
        /* istanbul ignore next */
        if (!line || !line.trim()) return;
        const parts = line.split("|");
        const name = (parts[0] || "").trim();
        const url = normalizeUrl((parts[1] || "").trim());
        if (name) {
          shoppingList.push({ name, url, previewUrl: null });
          shopImageFiles.push(null);
        }
      });
    }

    addBtn.addEventListener("click", addLink);
    itemInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addLink();
      }
    });
    linkInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addLink();
      }
    });
    formEl.addEventListener("submit", (event) => {
      const hasClientErrors = renderRequiredFieldErrors();
      if (hasClientErrors) {
        event.preventDefault();
        return;
      }
      cleanIngredientsField();
      syncShoppingField();
      syncShopImagesInput();
      persistFiles(imageInput, IMG_STORAGE_KEY);
    });

    if (!isBound) {
      try {
        w.sessionStorage.removeItem(IMG_STORAGE_KEY);
      } catch (err) {}
    } else if (hasErrors) {
      restoreFiles(imageInput, IMG_STORAGE_KEY, renderImagesList);
    }

    bootstrapExisting();
    renderList();
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      initCreateRecipe,
      normalizeUrl
    };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initCreateRecipe(global);
    /* istanbul ignore next */
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
