(function (global) {
  function clearStoredFiles(win, storageKey) {
    /* istanbul ignore next */
    if (!win || !storageKey) return;
    try {
      win.sessionStorage.removeItem(storageKey);
    } catch (err) {}
  }

  function createImageManager({
    w,
    doc,
    imageInput,
    imageList,
    storageKey,
    setInputFiles: setFiles,
    getFiles: getFilesFn,
    persistFiles: persistFn,
    restoreFiles: restoreFn
  }) {
    const state = {
      imageFiles: [],
      imagePreviewUrls: []
    };

    const fileKey = (file) => `${file.name}-${file.lastModified || 0}-${file.size || 0}`;

    function renderImagesList() {
      /* istanbul ignore next */
      if (!imageInput || !imageList) return;
      state.imagePreviewUrls.forEach((url) => {
        try {
          w.URL.revokeObjectURL(url);
        } catch (err) {
          /* istanbul ignore next */
        }
      });
      state.imagePreviewUrls = [];
      if (!state.imageFiles.length) {
        imageList.innerHTML = "";
        return;
      }
      const items = state.imageFiles.map((f, idx) => {
        const url = w.URL && typeof w.URL.createObjectURL === "function" ? w.URL.createObjectURL(f) : null;
        if (url) state.imagePreviewUrls.push(url);
        return { name: f.name, url, idx };
      });
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
        btn.addEventListener("click", () => {
          const idx = parseInt(btn.dataset.idx, 10);
          removeImageAt(idx);
        });
      });
    }

    function hydrateImagesFromInput() {
      const current = getFilesFn(imageInput) ? Array.from(getFilesFn(imageInput)) : [];
      state.imageFiles = current;
      renderImagesList();
    }

    function syncImageFiles(files) {
      state.imageFiles = Array.from(files);
      if (imageInput) {
        setFiles(imageInput, files);
      }
      renderImagesList();
      persistFn(w, imageInput, storageKey);
    }

    function removeImageAt(idx) {
      if (idx < 0 || idx >= state.imageFiles.length) return;
      const next = state.imageFiles.filter((_, i) => i !== idx);
      syncImageFiles(next);
    }

    function handleInputChange() {
      const selected = getFilesFn(imageInput) ? Array.from(getFilesFn(imageInput)) : [];
      if (!selected.length) {
        renderImagesList();
        return;
      }
      const existingMap = new Map(state.imageFiles.map((f) => [fileKey(f), f]));
      selected.forEach((f) => {
        const key = fileKey(f);
        if (!existingMap.has(key)) {
          existingMap.set(key, f);
        }
      });
      const merged = Array.from(existingMap.values());
      syncImageFiles(merged);
    }

    function bind() {
      if (!imageInput) return;
      hydrateImagesFromInput();
      imageInput.addEventListener("change", handleInputChange);
    }

    function restoreFromStorage() {
      restoreFn(w, imageInput, storageKey, hydrateImagesFromInput);
    }

    function persistSelection() {
      persistFn(w, imageInput, storageKey);
    }

    return {
      bind,
      renderImagesList,
      hydrateImagesFromInput,
      removeImageAt,
      syncImageFiles,
      restoreFromStorage,
      persistSelection
    };
  }

  const api = {
    clearStoredFiles,
    createImageManager
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  /* istanbul ignore next */
  if (global) {
    global.createRecipeImages = api;
  }
})(typeof window !== "undefined" ? window : null);
