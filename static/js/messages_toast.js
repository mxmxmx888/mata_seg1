const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

function resolveWindow(win) {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
}

function markInitialized(w, flag) {
  if (w[flag]) return false;
  w[flag] = true;
  return true;
}

function applyToast(w, toastEl, duration) {
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
}

function initMessagesToast(win) {
  const w = resolveWindow(win);
  if (!w || !markInitialized(w, "__messagesToastInitialized")) return;
  const toasts = Array.from(w.document.querySelectorAll(".toast"));
  toasts.forEach((toastEl) => applyToast(w, toastEl, 2000));
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
