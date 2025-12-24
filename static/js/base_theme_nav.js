(function (global) {
  function setInitialTheme(win, doc) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    const d = doc || (typeof document !== "undefined" ? document : undefined);
    /* istanbul ignore next */
    if (!w || !d) return;

    const prefersDark = w.matchMedia && w.matchMedia("(prefers-color-scheme: dark)");
    const theme = prefersDark && prefersDark.matches ? "dark" : "light";
    d.documentElement.dataset.theme = theme;
    d.documentElement.style.colorScheme = theme;
  }

  function attachNavSolid(nav, win) {
    /* istanbul ignore next */
    if (!nav || !win) return;
    const toggleNavSolid = () => {
      if (win.scrollY > 40) {
        nav.classList.add("navbar-solid");
      } else {
        nav.classList.remove("navbar-solid");
      }
    };
    toggleNavSolid();
    win.addEventListener("scroll", toggleNavSolid);
  }

  function attachThemeSync(win, doc) {
    /* istanbul ignore next */
    if (!win || !doc) return;
    const prefersDark = win.matchMedia && win.matchMedia("(prefers-color-scheme: dark)");
    const applyThemeFromSystem = () => {
      const theme = prefersDark && prefersDark.matches ? "dark" : "light";
      doc.documentElement.dataset.theme = theme;
      doc.documentElement.style.colorScheme = theme;
      if (doc.body) {
        doc.body.dataset.theme = theme;
      }
    };

    applyThemeFromSystem();
    if (prefersDark && prefersDark.addEventListener) {
      prefersDark.addEventListener("change", applyThemeFromSystem);
    }
  }

  function attachCollapseFallback(doc, win) {
    /* istanbul ignore next */
    if (!doc || (win && win.bootstrap && win.bootstrap.Collapse)) return;
    doc.querySelectorAll('[data-bs-toggle="collapse"]').forEach((toggle) => {
      const targetSelector = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
      /* istanbul ignore next */
      if (!targetSelector) return;
      const target = doc.querySelector(targetSelector);
      /* istanbul ignore next */
      if (!target) return;

      toggle.addEventListener("click", (event) => {
        event.preventDefault();
        const isOpen = target.classList.toggle("show");
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        toggle.classList.toggle("collapsed", !isOpen);
      });
    });
  }

  function attachDropdownFallback(doc, win) {
    /* istanbul ignore next */
    if (!doc || (win && win.bootstrap && win.bootstrap.Dropdown)) return;
    doc.querySelectorAll('[data-bs-toggle="dropdown"]').forEach((toggle) => {
      const menu = toggle.nextElementSibling;
      /* istanbul ignore next */
      if (!menu || !menu.classList.contains("dropdown-menu")) return;

      toggle.addEventListener("click", (event) => {
        event.preventDefault();
        menu.classList.toggle("show");
      });

      doc.addEventListener("click", (event) => {
        /* istanbul ignore next */
        if (!toggle.closest(".dropdown")) return;
        if (!toggle.closest(".dropdown").contains(event.target)) {
          menu.classList.remove("show");
        }
      });
    });
  }

  function attachTabFallback(doc, win) {
    /* istanbul ignore next */
    if (!doc || (win && win.bootstrap && win.bootstrap.Tab)) return;
    doc.querySelectorAll('[data-bs-toggle="tab"], [data-bs-toggle="pill"]').forEach((toggle) => {
      toggle.addEventListener("click", (event) => {
        event.preventDefault();

        const targetSelector = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
        /* istanbul ignore next */
        if (!targetSelector) return;

        const target = doc.querySelector(targetSelector);
        /* istanbul ignore next */
        if (!target) return;

        const tablist = toggle.closest('[role="tablist"]');
        if (tablist) {
          tablist.querySelectorAll('[data-bs-toggle="tab"], [data-bs-toggle="pill"]').forEach((btn) => {
            btn.classList.remove("active");
            btn.setAttribute("aria-selected", "false");
          });
        }

        toggle.classList.add("active");
        toggle.setAttribute("aria-selected", "true");

        const tabContent = target.closest(".tab-content");
        if (tabContent) {
          tabContent.querySelectorAll(".tab-pane").forEach((pane) => {
            pane.classList.remove("active", "show");
          });
        }

        target.classList.add("active", "show");
      });
    });
  }

  function convertAuthLabelsToPlaceholders(doc) {
    /* istanbul ignore next */
    if (!doc) return;
    doc.querySelectorAll(".auth-card form").forEach((form) => {
      form.querySelectorAll("label").forEach((label) => {
        const id = label.getAttribute("for");
        /* istanbul ignore next */
        if (!id) return;
        const input = form.querySelector("#" + id);
        /* istanbul ignore next */
        if (!input) return;
        if (!input.placeholder) {
          input.placeholder = label.textContent.trim();
        }
        label.style.display = "none";
      });
    });
  }

    function autosizeDashboardFilters(doc, win) {
      /* istanbul ignore next */
      if (!doc || !win) return;
      const dashboardSelects = doc.querySelectorAll(".dashboard-filter-select");

      function autosize(select) {
        /* istanbul ignore next */
        if (!select) return;

        const selectedOption = select.options[select.selectedIndex];
        /* istanbul ignore next */
        if (!selectedOption) return;

      const measuringSpan = doc.createElement("span");
      const computed = win.getComputedStyle(select);

      measuringSpan.textContent = selectedOption.text;
      measuringSpan.style.position = "fixed";
      measuringSpan.style.visibility = "hidden";
      measuringSpan.style.whiteSpace = "nowrap";
      measuringSpan.style.font = computed.font;

      doc.body.appendChild(measuringSpan);
      const textWidth = measuringSpan.getBoundingClientRect().width;
      doc.body.removeChild(measuringSpan);

      const horizontalPadding =
        parseFloat(computed.paddingLeft || "0") +
        parseFloat(computed.paddingRight || "0") +
        20;

      select.style.width = `${textWidth + horizontalPadding}px`;
    }

    dashboardSelects.forEach((select) => {
      autosize(select);
      select.addEventListener("change", () => {
        autosize(select);
      });
    });
  }

  function initBaseInteractions(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    /* istanbul ignore next */
    if (!w || !w.document) return;
    const doc = w.document;

    const nav = doc.querySelector(".navbar-recipi");
    const isAuth = doc.body && doc.body.classList.contains("auth-body");

    if (nav && !isAuth) {
      attachNavSolid(nav, w);
    }

    attachThemeSync(w, doc);
    attachCollapseFallback(doc, w);
    attachDropdownFallback(doc, w);
    attachTabFallback(doc, w);
    convertAuthLabelsToPlaceholders(doc);
    autosizeDashboardFilters(doc, w);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      setInitialTheme,
      initBaseInteractions
    };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    setInitialTheme(global, global.document);
    const runInit = () => initBaseInteractions(global);
    /* istanbul ignore next */
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
