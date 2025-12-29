{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const safeRequire = (path) => {
  try {
    return require(path);
  } catch (err) {
    return {};
  }
};

const loadModule = (path, globalKey) => {
  if (hasModuleExports) return safeRequire(path);
  const globalVal = globalWindow && globalWindow[globalKey];
  return globalVal || {};
};

const validation = loadModule("./create_recipe_validation", "createRecipeValidation");
const images = loadModule("./create_recipe_images", "createRecipeImages");
const shopping = loadModule("./create_recipe_shopping", "createRecipeShopping");

const noop = () => {};

const normalizeUrl = (url) => (!url ? "" : /^https?:\/\//i.test(url) ? url : "https://" + url);

const parseJsonSafe = (raw) => {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
};

const parseArrayFrom = (raw) => {
  const parsed = parseJsonSafe(raw);
  if (Array.isArray(parsed)) return parsed;
  if (typeof parsed === "string") {
    const nested = parseJsonSafe(parsed);
    if (Array.isArray(nested)) return nested;
  }
  return null;
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
      get: () => normalized,
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
        data: reader.result,
      });
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });

const clearStorageKey = (win, storageKey) => {
  try {
    win.sessionStorage.removeItem(storageKey);
  } catch (err) {
    /* ignore */
  }
};

const writeStorage = (win, storageKey, payload) => {
  try {
    win.sessionStorage.setItem(storageKey, JSON.stringify(payload));
  } catch (err) {
    /* ignore */
  }
};

const persistFiles = (win, input, storageKey) => {
  if (!win || !input || !storageKey) return Promise.resolve();
  const files = getFiles(input);
  if (!files || !files.length) {
    clearStorageKey(win, storageKey);
    return Promise.resolve();
  }
  const limited = Array.from(files).slice(0, 10);
  writeStorage(win, storageKey, limited.map((file) => ({ name: file.name, type: file.type, lastModified: file.lastModified, data: null })));
  return Promise.all(limited.map((file) => serializeFile(win, file))).then((results) => {
    const cleaned = results.filter(Boolean);
    if (!cleaned.length) return clearStorageKey(win, storageKey);
    writeStorage(win, storageKey, cleaned);
  });
};

const fetchStoredEntries = (win, storageKey) => {
  try {
    const parsed = JSON.parse(win.sessionStorage.getItem(storageKey) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    return [];
  }
};

const makeRestoredFile = async (win, item) => {
  if (!item || !item.data) return null;
  try {
    const response = await win.fetch(item.data);
    const blob = await response.blob();
    return new win.File([blob], item.name || "upload", {
      type: item.type || blob.type || "application/octet-stream",
      lastModified: item.lastModified || Date.now(),
    });
  } catch (err) {
    return null;
  }
};

const restoreFiles = async (win, input, storageKey, onAfterRestore) => {
  if (!win || !input || !storageKey) return;
  const stored = fetchStoredEntries(win, storageKey);
  if (!stored.length) return;
  const canUseDataTransfer = typeof win.DataTransfer !== "undefined";
  const dataTransfer = canUseDataTransfer ? new win.DataTransfer() : null;
  const results = await Promise.all(stored.map((item) => makeRestoredFile(win, item)));
  const files = results.filter(Boolean);
  if (!files.length) return;
  if (dataTransfer) {
    files.forEach((file) => dataTransfer.items.add(file));
  }
  setInputFiles(input, dataTransfer ? dataTransfer.files : files);
  if (typeof onAfterRestore === "function") onAfterRestore();
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

const fieldMissing = (field, getFilesSafe) => {
  const candidateFiles = field.type === "file" ? getFilesSafe(field) : null;
  const missingText = !(field.value || "").trim();
  const missingValidity = field.validity ? field.validity.valueMissing : missingText;
  return missingValidity && !(candidateFiles && candidateFiles.length);
};

const removeFieldErrors = (field) => {
  const container = field.closest(".mb-3") || field.parentElement;
  if (!container) return;
  container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
};

const renderRequiredFieldErrors = (doc, formEl, fields, getFilesSafe) => {
  if (!formEl) return false;
  let hasClientErrors = false;
  formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
  fields.forEach((field) => {
    if (fieldMissing(field, getFilesSafe)) {
      hasClientErrors = true;
      renderFieldError(doc, field);
    }
  });
  return hasClientErrors;
};

const bindRequiredListeners = (fields) => {
  fields.forEach((field) => {
    field.addEventListener("input", () => removeFieldErrors(field));
    field.addEventListener("change", () => removeFieldErrors(field));
  });
};

const createRequiredFieldValidator =
  validation.createRequiredFieldValidator ||
  ((doc, formEl, requiredFields, getFilesFn) => {
    const getFilesSafe = typeof getFilesFn === "function" ? getFilesFn : () => null;
    const fields = requiredFields || [];
    return {
      renderRequiredFieldErrors: () => renderRequiredFieldErrors(doc, formEl, fields, getFilesSafe),
      bindRequiredListeners: () => bindRequiredListeners(fields),
    };
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
    persistSelection: noop,
  }));

const createShoppingManager =
  shopping.createShoppingManager ||
  (() => ({
    addLink: noop,
    bind: noop,
    bootstrapExisting: noop,
    renderList: noop,
    syncShoppingField: noop,
    syncShopImagesInput: noop,
  }));

const api = {
  normalizeUrl,
  parseArrayFrom,
  setInputFiles,
  getFiles,
  persistFiles,
  restoreFiles,
  clearStoredFiles,
  createRequiredFieldValidator,
  createImageManager,
  createShoppingManager,
};

if (hasModuleExports) {
  module.exports = api;
}

/* istanbul ignore next */
if (globalWindow) {
  globalWindow.createRecipeHelpers = api;
}
}
