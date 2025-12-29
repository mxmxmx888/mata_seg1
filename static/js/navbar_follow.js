{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const resolveWindow = (win) => win || globalWindow;
const markInitialized = (w, flag) => {
  if (!w || w[flag]) return false;
  w[flag] = true;
  return true;
};

const getCsrfToken = (form) => {
  const tokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
  return tokenInput ? tokenInput.value : undefined;
};

const buildFetchHeaders = (form) => {
  const csrfToken = getCsrfToken(form);
  return Object.assign({ "X-Requested-With": "XMLHttpRequest" }, csrfToken ? { "X-CSRFToken": csrfToken } : {});
};

const toggleFollowState = (button, currentState) => {
  const nextIsFollowing = currentState === "not-following";
  button.textContent = nextIsFollowing ? "Following" : "Follow";
  button.classList.toggle("btn-primary", !nextIsFollowing);
  button.classList.toggle("btn-outline-light", nextIsFollowing);
  button.setAttribute("data-follow-state", nextIsFollowing ? "following" : "not-following");
};

const wireFollowForms = (doc, w) => {
  doc.querySelectorAll(".notification-follow-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const button = form.querySelector("button[data-follow-state]");
      if (!button) {
        form.submit();
        return;
      }
      const currentState = button.getAttribute("data-follow-state") || "not-following";
      const formData = new w.FormData(form);
      w
        .fetch(form.action, { method: "POST", body: formData, headers: buildFetchHeaders(form), redirect: "manual" })
        .then(() => toggleFollowState(button, currentState))
        .catch(() => form.submit());
    });
  });
};

const wireNotificationItems = (doc, w) => {
  doc.querySelectorAll(".notification-item[data-post-url]").forEach((item) => {
    item.addEventListener("click", (event) => {
      const url = item.dataset.postUrl;
      if (!url || event.target.closest("a, button, form")) return;
      w.location.href = url;
    });
  });
};

const wireFollowRequestForms = (doc, w) => {
  doc.querySelectorAll(".notification-follow-request-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const action = form.dataset.action;
      const item = form.closest("[data-notification-id]");
      const message = item ? item.querySelector(".notification-message") : null;
      const actionsRow = item ? item.querySelector(".notification-follow-request-actions") : null;
      w
        .fetch(form.action, { method: "POST", body: new w.FormData(form), headers: buildFetchHeaders(form), redirect: "manual" })
        .then(() => {
          if (!item) return;
          if (action === "accept") {
            if (message) message.textContent = "started following you.";
            actionsRow?.remove();
          } else if (action === "reject") {
            item.remove();
          }
        })
        .catch(() => form.submit());
    });
  });
};

const initNavbarFollow = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || !markInitialized(w, "__navbarFollowInitialized")) return;
  const doc = w.document;
  wireFollowForms(doc, w);
  wireNotificationItems(doc, w);
  wireFollowRequestForms(doc, w);
};

const autoInit = () => {
  const w = resolveWindow();
  if (!w || !w.document) return;
  const runInit = () => initNavbarFollow(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initNavbarFollow };
}

/* istanbul ignore next */
autoInit();
}
