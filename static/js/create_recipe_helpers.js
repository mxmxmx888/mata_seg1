const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const loadModule = (path, globalKey) => {
  if (hasModuleExports) {
    try {
      return require(path);
    } catch (err) {
      return {};
    }
  }
  return globalWindow && globalWindow[globalKey] ? globalWindow[globalKey] : {};
};

const validation = loadModule("./create_recipe_validation", "createRecipeValidation");
const images = loadModule("./create_recipe_images", "createRecipeImages");
const shopping = loadModule("./create_recipe_shopping", "createRecipeShopping");

const noop = () => {};

const normalizeUrl = (url) => {
  if (!url) return "";
  return /^https?:\/\//i.test(url) ? url : "https://" + url;
};

const normalizeToFileList = (files) => {
  if (!(files instanceof FileList) && typeof DataTransfer !== "undefined") {
    const dt = new DataTransfer();
    Array.from(files || []).forEach((f) => f && dt.items.add(f));
    return dt.files;
  }
  return files;
};

const applyNativeFiles = (input, normalized) => {
  const descriptor =
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input) || {}, "files") ||
    Object.getOwnPropertyDescriptor(input, "files") ||
    (typeof HTMLInputElement !== "undefined"
      ? Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "files")
      : null);
  try {
    if (descriptor && descriptor.set) {
      descriptor.set.call(input, normalized);
    } else {
      input.files = normalized;
    }
  } catch (err) {
    /* ignore */
  }
};

const setInputFiles = (input, files) => {
  if (!input || !files) return;
  const normalized = normalizeToFileList(files);
  input.__mockFiles = normalized;
  applyNativeFiles(input, normalized);
  if (input.files && input.files.length === normalized.length) return;
  try {
    Object.defineProperty(input, "files", {
      configurable: true,
      get: () => normalized
    });
  } catch (err) {
    /* ignore */
  }
};

const getFiles = (input) => {
  if (!input) return null;
  const real = input.files;
  if (real && real.length) return real;
  return input.__mockFiles || real;
};

const clearStoredFiles =
  images.clearStoredFiles ||
  ((win, storageKey) => {
    if (!win || !storageKey) return;
    try {
      win.sessionStorage.removeItem(storageKey);
    } catch (err) {
      /* ignore */
    }
  });

const serializeFile = (win, file) =>
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
  });

const persistFiles = (win, input, storageKey) => {
  if (!win || !input || !storageKey) return;
  const files = getFiles(input);
  if (!files || !files.length) {
    try {
      win.sessionStorage.removeItem(storageKey);
    } catch (err) {
      /* ignore */
    }
    return;
  }
  const entries = Array.from(files)
    .slice(0, 10)
    .map((file) => serializeFile(win, file));
  Promise.all(entries).then((results) => {
    const cleaned = results.filter(Boolean);
    if (!cleaned.length) {
      try {
        win.sessionStorage.removeItem(storageKey);
      } catch (err) {
        /* ignore */
      }
      return;
    }
    try {
      win.sessionStorage.setItem(storageKey, JSON.stringify(cleaned));
    } catch (err) {
      /* ignore */
    }
  });
};

const restoreFiles = async (win, input, storageKey, onAfterRestore) => {
  if (!win || !input || !storageKey) return;
  let stored = [];
  try {
    stored = JSON.parse(win.sessionStorage.getItem(storageKey) || "[]");
  } catch (err) {
    return;
  }
  if (!Array.isArray(stored) || !stored.length) return;
  const canUseDataTransfer = typeof win.DataTransfer !== "undefined";
  const dataTransfer = canUseDataTransfer ? new win.DataTransfer() : null;
  const fallbackFiles = [];
  for (const item of stored) {
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
      /* ignore */
    }
  }
  const restored = dataTransfer ? dataTransfer.files : fallbackFiles;
  if (restored && restored.length) {
    setInputFiles(input, restored);
    if (typeof onAfterRestore === "function") onAfterRestore();
  }
};

const renderFieldError = (doc, field) => {
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
};

const createRequiredFieldValidator =
  validation.createRequiredFieldValidator ||
  ((doc, formEl, requiredFields, getFilesFn) => {
    const getFilesSafe = typeof getFilesFn === "function" ? getFilesFn : () => null;
    const fields = requiredFields || [];
    const removeErrors = (field) => {
      const container = field.closest(".mb-3") || field.parentElement;
      if (!container) return;
      container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
    };
    const renderRequiredFieldErrors = () => {
      if (!formEl) return false;
      let hasClientErrors = false;
      formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
      fields.forEach((field) => {
        const candidateFiles = field.type === "file" ? getFilesSafe(field) : null;
        const missingText = !(field.value || "").trim();
        const missingValidity = field.validity ? field.validity.valueMissing : missingText;
        const isMissing = missingValidity && !(candidateFiles && candidateFiles.length);
        if (isMissing) {
          hasClientErrors = true;
          renderFieldError(doc, field);
        }
      });
      return hasClientErrors;
    };
    const bindRequiredListeners = () => {
      fields.forEach((field) => {
        field.addEventListener("input", () => removeErrors(field));
        field.addEventListener("change", () => removeErrors(field));
      });
    };
    return { renderRequiredFieldErrors, bindRequiredListeners };
  });

const createImageManager =
  images.createImageManager ||
  (() => ({
    bind: noop,
    renderImagesList: noop,
    hydrateImagesFromInput: noop,
    removeImageAt: noop,
    syncImageFiles: noop,
    restoreFromStorage: noop,
    persistSelection: noop
  }));

const createShoppingManager =
  shopping.createShoppingManager ||
  (() => ({
    addLink: noop,
    bind: noop,
    bootstrapExisting: noop,
    renderList: noop,
    syncShoppingField: noop,
    syncShopImagesInput: noop
  }));

const api = {
  normalizeUrl,
  setInputFiles,
  getFiles,
  persistFiles,
  restoreFiles,
  clearStoredFiles,
  createRequiredFieldValidator,
  createImageManager,
  createShoppingManager
};

if (hasModuleExports) {
  module.exports = api;
}

/* istanbul ignore next */
if (globalWindow) {
  globalWindow.createRecipeHelpers = api;
}
