(function (global) {
  function initMessagesToast(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__messagesToastInitialized) return;
    w.__messagesToastInitialized = true;

    const doc = w.document;
    const toastEls = Array.from(doc.querySelectorAll(".toast"));
    toastEls.forEach((toastEl) => {
      const duration = 2000;
      const hasBootstrap = !!(w.bootstrap && w.bootstrap.Toast);
      const toast = hasBootstrap ? new w.bootstrap.Toast(toastEl, { delay: duration, autohide: true }) : null;

      if (toast && typeof toast.show === "function") {
        toast.show();
      } else {
        toastEl.classList.add("show");
      }

      w.setTimeout(() => {
        if (toast && typeof toast.hide === "function") {
          toast.hide();
        } else {
          toastEl.classList.remove("show");
          toastEl.classList.add("hide");
        }
      }, duration);
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initMessagesToast };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initMessagesToast(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
