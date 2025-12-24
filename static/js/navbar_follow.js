(function (global) {
  function initNavbarFollow(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__navbarFollowInitialized) return;
    w.__navbarFollowInitialized = true;

    const doc = w.document;

    const getCsrfToken = (form) => {
      const tokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
      return tokenInput ? tokenInput.value : undefined;
    };

    const buildFetchHeaders = (form) => {
      const csrfToken = getCsrfToken(form);
      return Object.assign({ "X-Requested-With": "XMLHttpRequest" }, csrfToken ? { "X-CSRFToken": csrfToken } : {});
    };

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
          .fetch(form.action, {
            method: "POST",
            body: formData,
            headers: buildFetchHeaders(form),
            redirect: "manual"
          })
          .then(() => {
            if (currentState === "not-following") {
              button.textContent = "Following";
              button.classList.remove("btn-primary");
              button.classList.add("btn-outline-light");
              button.setAttribute("data-follow-state", "following");
            } else {
              button.textContent = "Follow";
              button.classList.remove("btn-outline-light");
              button.classList.add("btn-primary");
              button.setAttribute("data-follow-state", "not-following");
            }
          })
          .catch(() => {
            form.submit();
          });
      });
    });

    doc.querySelectorAll(".notification-item[data-post-url]").forEach((item) => {
      item.addEventListener("click", (event) => {
        const url = item.dataset.postUrl;
        if (!url) return;

        if (event.target.closest("a, button, form")) {
          return;
        }

        w.location.href = url;
      });
    });

    doc.querySelectorAll(".notification-follow-request-form").forEach((form) => {
      form.addEventListener("submit", (event) => {
        event.preventDefault();

        const action = form.dataset.action;
        const item = form.closest("[data-notification-id]");
        const message = item ? item.querySelector(".notification-message") : null;
        const actionsRow = item ? item.querySelector(".notification-follow-request-actions") : null;

        w
          .fetch(form.action, {
            method: "POST",
            body: new w.FormData(form),
            headers: buildFetchHeaders(form),
            redirect: "manual"
          })
          .then(() => {
            if (!item) return;

            if (action === "accept") {
              if (message) {
                message.textContent = "started following you.";
              }
              if (actionsRow) {
                actionsRow.remove();
              }
            } else if (action === "reject") {
              item.remove();
            }
          })
          .catch(() => {
            form.submit();
          });
      });
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initNavbarFollow };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initNavbarFollow(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
