(function (global) {
  function loadModule(path, globalKey) {
    if (typeof module !== "undefined" && module.exports) {
      try {
        return require(path);
      } catch (err) {
        return {};
      }
    }
    return global && global[globalKey] ? global[globalKey] : {};
  }

  const validation = loadModule("./create_recipe_validation", "createRecipeValidation");
  const images = loadModule("./create_recipe_images", "createRecipeImages");
  const shopping = loadModule("./create_recipe_shopping", "createRecipeShopping");

  const noop = () => {};

  function normalizeUrl(url) {
    if (!url) return "";
    return /^https?:\/\//i.test(url) ? url : "https://" + url;
  }

  function setInputFiles(input, files) {
    /* istanbul ignore next */
    if (!input || !files) return;

    // Normalize to a FileList so the browser will include it on submit.
    let normalized = files;
    const asArray = Array.from(files || []);
    if (!(files instanceof FileList) && typeof DataTransfer !== "undefined") {
      const dt = new DataTransfer();
      asArray.forEach((f) => f && dt.items.add(f));
      normalized = dt.files;
    }

    input.__mockFiles = normalized;

    const descriptor =
      Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input) || {}, "files") ||
      Object.getOwnPropertyDescriptor(input, "files") ||
      (typeof HTMLInputElement !== "undefined"
        ? Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "files")
        : null);

    try {
      // Prefer native setter so the value is used for form submission.
      if (descriptor && descriptor.set) {
        descriptor.set.call(input, normalized);
      } else {
        input.files = normalized;
      }
    } catch (err) {
      /* istanbul ignore next */
    }

    if (input.files && input.files.length === normalized.length) {
      return;
    }

    try {
      Object.defineProperty(input, "files", {
        configurable: true,
        get: () => normalized
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

  function persistFiles(win, input, storageKey) {
    /* istanbul ignore next */
    if (!win || !input || !storageKey) return;
    const files = getFiles(input);
    if (!files || !files.length) {
      try {
        win.sessionStorage.removeItem(storageKey);
      } catch (err) {}
      return;
    }

    const entries = Array.from(files)
      .slice(0, 10)
      .map(
        (file) =>
          new Promise((resolve) => {
            const reader = new win.FileReader();
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
          win.sessionStorage.removeItem(storageKey);
        } catch (err) {}
        return;
      }
      try {
        win.sessionStorage.setItem(storageKey, JSON.stringify(cleaned));
      } catch (err) {}
    });
  }

  async function restoreFiles(win, input, storageKey, onAfterRestore) {
    /* istanbul ignore next */
    if (!win || !input || !storageKey) return;
    let stored = [];
    try {
      stored = JSON.parse(win.sessionStorage.getItem(storageKey) || "[]");
    } catch (err) {
      /* istanbul ignore next */
      return;
    }
    /* istanbul ignore next */
    if (!Array.isArray(stored) || !stored.length) return;

    const canUseDataTransfer = typeof win.DataTransfer !== "undefined";
    const dataTransfer = canUseDataTransfer ? new win.DataTransfer() : null;
    const fallbackFiles = [];
    for (const item of stored) {
      /* istanbul ignore next */
      if (!item || !item.data) continue;
      try {
        const response = await win.fetch(item.data);
        const blob = await response.blob();
        const file = new win.File([blob], item.name || "upload", {
          type: item.type || blob.type || "application/octet-stream",
          lastModified: item.lastModified || Date.now()
        });
        if (dataTransfer) {
          dataTransfer.items.add(file);
        } else {
          fallbackFiles.push(file);
        }
      } catch (err) {
        /* istanbul ignore next */
        continue;
      }
    }

    const restored = dataTransfer ? dataTransfer.files : fallbackFiles;
    if (restored && restored.length) {
      setInputFiles(input, restored);
      if (typeof onAfterRestore === "function") onAfterRestore();
    }
  }

  const api = {
    normalizeUrl,
    setInputFiles,
    getFiles,
    persistFiles,
    restoreFiles,
    clearStoredFiles:
      images.clearStoredFiles ||
      ((win, storageKey) => {
        /* istanbul ignore next */
        if (!win || !storageKey) return;
        try {
          win.sessionStorage.removeItem(storageKey);
        } catch (err) {}
      }),
    createRequiredFieldValidator:
      validation.createRequiredFieldValidator ||
      ((doc, formEl, requiredFields, getFilesFn) => {
        const getFilesSafe = typeof getFilesFn === "function" ? getFilesFn : () => null;
        const fields = requiredFields || [];
        return {
          renderRequiredFieldErrors: () => {
            /* istanbul ignore next */
            if (!formEl) return false;
            let hasClientErrors = false;
            formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
            fields.forEach((field) => {
              const candidateFiles = field.type === "file" ? getFilesSafe(field) : null;
              let isMissing = field.validity ? field.validity.valueMissing : !(field.value || "").trim();
              if (candidateFiles && candidateFiles.length) {
                isMissing = false;
              }
              if (isMissing) {
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
                  field.insertAdjacentElement("afterend", message);
                }
              }
            });
            return hasClientErrors;
          },
          bindRequiredListeners: () => {
            fields.forEach((field) => {
              field.addEventListener("input", () => {
                const container = field.closest(".mb-3") || field.parentElement;
                /* istanbul ignore next */
                if (!container) return;
                container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
              });
              field.addEventListener("change", () => {
                const container = field.closest(".mb-3") || field.parentElement;
                /* istanbul ignore next */
                if (!container) return;
                container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
              });
            });
          }
        };
      }),
    createImageManager:
      images.createImageManager ||
      (() => ({
        bind: noop,
        renderImagesList: noop,
        hydrateImagesFromInput: noop,
        removeImageAt: noop,
        syncImageFiles: noop,
        restoreFromStorage: noop,
        persistSelection: noop
      })),
    createShoppingManager:
      shopping.createShoppingManager ||
      (() => ({
        addLink: noop,
        bind: noop,
        bootstrapExisting: noop,
        renderList: noop,
        syncShoppingField: noop,
        syncShopImagesInput: noop
      }))
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  /* istanbul ignore next */
  if (global) {
    global.createRecipeHelpers = api;
  }
})(typeof window !== "undefined" ? window : null);
