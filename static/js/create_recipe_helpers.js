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
    /* istanbul ignore next */
    if (typeof win.DataTransfer === "undefined") return;
    let stored = [];
    try {
      stored = JSON.parse(win.sessionStorage.getItem(storageKey) || "[]");
    } catch (err) {
      /* istanbul ignore next */
      return;
    }
    /* istanbul ignore next */
    if (!Array.isArray(stored) || !stored.length) return;

    const dataTransfer = new win.DataTransfer();
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

  const api = {
    normalizeUrl,
    setInputFiles,
    getFiles,
    persistFiles,
    restoreFiles
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  /* istanbul ignore next */
  if (global) {
    global.createRecipeHelpers = api;
  }
})(typeof window !== "undefined" ? window : null);
