{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const clearStoredFiles = (win, storageKey) => {
  if (!win || !storageKey) return;
  try {
    win.sessionStorage.removeItem(storageKey);
  } catch (err) {
    /* ignore */
  }
};

const fileKey = (file) => `${file.name}-${file.lastModified || 0}-${file.size || 0}`;

const buildState = () => ({ imageFiles: [], imagePreviewUrls: [] });

const revokePreviews = (w, urls) => {
  urls.forEach((url) => {
    try {
      w.URL.revokeObjectURL(url);
    } catch (err) {
      /* ignore */
    }
  });
};

const previewsFor = (w, files, state) =>
  files.map((f, idx) => {
    const url = w.URL && typeof w.URL.createObjectURL === "function" ? w.URL.createObjectURL(f) : null;
    if (url) state.imagePreviewUrls.push(url);
    return { name: f.name, url, idx };
  });

const renderImagesList = (w, state, imageList, imageInput, removeImageAt) => {
  if (!imageInput || !imageList) return;
  revokePreviews(w, state.imagePreviewUrls);
  state.imagePreviewUrls = [];
  if (!state.imageFiles.length) {
    imageList.innerHTML = "";
    return;
  }
  const items = previewsFor(w, state.imageFiles, state);
  imageList.innerHTML = items
    .map(
      ({ name, url, idx }) =>
        `<span class="image-preview-item" data-idx="${idx}">
          ${url ? `<img src="${url}" alt="${name}" class="image-thumb">` : ""}
          <span class="image-preview-name">${name}</span>
          <button type="button" class="image-remove" data-idx="${idx}" aria-label="Remove ${name}">&times;</button>
        </span>`
    )
    .join("");
  imageList.querySelectorAll(".image-remove").forEach((btn) => {
    btn.addEventListener("click", () => removeImageAt(parseInt(btn.dataset.idx, 10)));
  });
};

const hydrateImagesFromInput = (state, imageInput, imageList, w, getFilesFn, removeImageAt) => {
  state.imageFiles = getFilesFn(imageInput) ? Array.from(getFilesFn(imageInput)) : [];
  renderImagesList(w, state, imageList, imageInput, removeImageAt);
};

const syncImageFiles = (state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, files) => {
  state.imageFiles = Array.from(files);
  if (imageInput) {
    setFiles(imageInput, files);
  }
  renderImagesList(w, state, imageList, imageInput, (idx) =>
    removeImageAt(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, idx)
  );
  persistFn(w, imageInput, storageKey);
};

const removeImageAt = (state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, idx) => {
  if (idx < 0 || idx >= state.imageFiles.length) return;
  const next = state.imageFiles.filter((_, i) => i !== idx);
  syncImageFiles(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, next);
};

const handleInputChange = (state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey) => {
  const current = getFilesFn(imageInput) ? Array.from(getFilesFn(imageInput)) : [];
  if (!current.length) {
    renderImagesList(w, state, imageList, imageInput, (idx) =>
      removeImageAt(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, idx)
    );
    return;
  }
  const existingMap = new Map(state.imageFiles.map((f) => [fileKey(f), f]));
  current.forEach((f) => {
    const key = fileKey(f);
    if (!existingMap.has(key)) existingMap.set(key, f);
  });
  syncImageFiles(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, existingMap.values());
};

const bind = (state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, restoreFn, storageKey) => {
  if (!imageInput) return;
  const removeAt = (idx) =>
    removeImageAt(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, idx);
  const refresh = () => hydrateImagesFromInput(state, imageInput, imageList, w, getFilesFn, removeAt);
  refresh();
  if (!w.sessionStorage.getItem(storageKey) && state.imageFiles.length) {
    persistFn(w, imageInput, storageKey);
  }
  imageInput.addEventListener("change", () =>
    handleInputChange(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey)
  );
  restoreFn(w, imageInput, storageKey, refresh);
};

const persistSelection = (w, imageInput, persistFn, storageKey) => {
  persistFn(w, imageInput, storageKey);
};

const createImageManager = (params) => {
  const state = buildState();
  const { w, imageInput, imageList, storageKey, setInputFiles: setFiles, getFiles: getFilesFn, persistFiles: persistFn, restoreFiles: restoreFn } =
    params;
  const removeAt = (idx) => removeImageAt(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, idx);
  const hydrate = () => hydrateImagesFromInput(state, imageInput, imageList, w, getFilesFn, removeAt);
  return {
    bind: () => bind(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, restoreFn, storageKey),
    renderImagesList: () => renderImagesList(w, state, imageList, imageInput, removeAt),
    hydrateImagesFromInput: hydrate,
    removeImageAt: removeAt,
    syncImageFiles: (files) => syncImageFiles(state, imageInput, imageList, w, setFiles, getFilesFn, persistFn, storageKey, files),
    restoreFromStorage: () => restoreFn(w, imageInput, storageKey, hydrate),
    persistSelection: () => persistSelection(w, imageInput, persistFn, storageKey),
  };
};

const api = { clearStoredFiles, createImageManager };

if (hasModuleExports) {
  module.exports = api;
}

/* istanbul ignore next */
if (globalWindow) {
  globalWindow.createRecipeImages = api;
}
}
