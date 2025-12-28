(() => {
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const TOAST_SELECTOR = ".toast";
const TOAST_DURATION = 2000;
const TOAST_CLEANUP_PADDING = 500;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const markInitialized = (w, flag) => {
  if (w[flag]) return false;
  w[flag] = true;
  return true;
};

const finalizeToast = (toastEl, toast) => {
  if (!toastEl) return;
  toastEl.classList.remove("show");
  toastEl.classList.add("hide");
  if (toast && typeof toast.dispose === "function") {
    toast.dispose();
  }
  toastEl.remove();
};

const applyToast = (w, toastEl, duration) => {
  if (!toastEl || toastEl.dataset.toastBound === "true") return;
  toastEl.dataset.toastBound = "true";
  const hasBootstrap = !!(w.bootstrap && w.bootstrap.Toast);
  const toast = hasBootstrap ? new w.bootstrap.Toast(toastEl, { delay: duration, autohide: true }) : null;
  const finish = () => finalizeToast(toastEl, toast);

  if (toast && typeof toast.show === "function") {
    toastEl.addEventListener("hidden.bs.toast", finish, { once: true });
    toast.show();
  } else {
    toastEl.classList.add("show");
  }

  w.setTimeout(() => {
    if (toast && typeof toast.hide === "function") {
      toast.hide();
      w.setTimeout(finish, 250);
    } else {
      finish();
    }
  }, duration);
};

const scheduleFallbackCleanup = (w, doc, duration) => {
  if (!w || !doc) return;
  w.setTimeout(() => {
    Array.from(doc.querySelectorAll(TOAST_SELECTOR)).forEach((toastEl) => finalizeToast(toastEl));
  }, duration + TOAST_CLEANUP_PADDING);
};

const observeNewToasts = (w, doc, duration) => {
  if (!doc || !doc.body || typeof w.MutationObserver === "undefined") return;
  const observer = new w.MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof w.HTMLElement)) return;
        if (node.matches(TOAST_SELECTOR)) {
          applyToast(w, node, duration);
        }
        node.querySelectorAll?.(TOAST_SELECTOR).forEach((toastEl) => applyToast(w, toastEl, duration));
      });
    });
  });
  observer.observe(doc.body, { childList: true, subtree: true });
};

function initMessagesToast(win) {
  const w = resolveWindow(win);
  const doc = w && w.document;
  scheduleFallbackCleanup(w, doc, TOAST_DURATION);
  if (!w || !markInitialized(w, "__messagesToastInitialized")) return;
  const toasts = Array.from(doc.querySelectorAll(TOAST_SELECTOR));
  toasts.forEach((toastEl) => applyToast(w, toastEl, TOAST_DURATION));
  observeNewToasts(w, doc, TOAST_DURATION);
}

function autoInitMessagesToast() {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initMessagesToast(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
}

if (hasModuleExports) {
  module.exports = { initMessagesToast };
}

/* istanbul ignore next */
autoInitMessagesToast();
})();
