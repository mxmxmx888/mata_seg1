{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow || (typeof window !== "undefined" ? window : null);
  return candidate && candidate.document ? candidate : null;
};

const setInitialTheme = (win, doc) => {
  const w = resolveWindow(win);
  const d = doc || (w && w.document);
  if (!w || !d) return;
  const prefersDark = w.matchMedia && w.matchMedia("(prefers-color-scheme: dark)");
  const theme = prefersDark && prefersDark.matches ? "dark" : "light";
  d.documentElement.dataset.theme = theme;
  d.documentElement.style.colorScheme = theme;
};

const attachNavSolid = (nav, win) => {
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
};

const applyThemeFromSystem = (prefersDark, doc) => {
  const theme = prefersDark && prefersDark.matches ? "dark" : "light";
  doc.documentElement.dataset.theme = theme;
  doc.documentElement.style.colorScheme = theme;
  if (doc.body) {
    doc.body.dataset.theme = theme;
  }
};

const attachThemeSync = (win, doc) => {
  if (!win || !doc) return;
  const prefersDark = win.matchMedia && win.matchMedia("(prefers-color-scheme: dark)");
  applyThemeFromSystem(prefersDark, doc);
  if (prefersDark && prefersDark.addEventListener) {
    prefersDark.addEventListener("change", (event) =>
      applyThemeFromSystem(event && typeof event.matches === "boolean" ? event : prefersDark, doc)
    );
  }
};

const attachCollapseFallback = (doc, win) => {
  if (!doc || (win && win.bootstrap && win.bootstrap.Collapse)) return;
  doc.querySelectorAll('[data-bs-toggle="collapse"]').forEach((toggle) => {
    const targetSelector = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
    if (!targetSelector) return;
    const target = doc.querySelector(targetSelector);
    if (!target) return;
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      const isOpen = target.classList.toggle("show");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      toggle.classList.toggle("collapsed", !isOpen);
    });
  });
};

const attachDropdownFallback = (doc, win) => {
  if (!doc || (win && win.bootstrap && win.bootstrap.Dropdown)) return;
  doc.querySelectorAll('[data-bs-toggle="dropdown"]').forEach((toggle) => {
    const menu = toggle.nextElementSibling;
    if (!menu || !menu.classList.contains("dropdown-menu")) return;
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      menu.classList.toggle("show");
    });
    doc.addEventListener("click", (event) => {
      const parent = toggle.closest(".dropdown");
      if (!parent) return;
      if (!parent.contains(event.target)) {
        menu.classList.remove("show");
      }
    });
  });
};

const activateTab = (doc, toggle, target) => {
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
    tabContent.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.remove("active", "show"));
  }
  target.classList.add("active", "show");
};

const attachTabFallback = (doc, win) => {
  if (!doc || (win && win.bootstrap && win.bootstrap.Tab)) return;
  const handleClick = (toggle) => (event) => {
    event.preventDefault();
    const targetSelector = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
    const target = targetSelector ? doc.querySelector(targetSelector) : null;
    if (target) activateTab(doc, toggle, target);
  };
  doc.querySelectorAll('[data-bs-toggle="tab"], [data-bs-toggle="pill"]').forEach((toggle) => {
    toggle.addEventListener("click", handleClick(toggle));
  });
};

const convertAuthLabelsToPlaceholders = (doc) => {
  if (!doc) return;
  doc.querySelectorAll(".auth-card form").forEach((form) => {
    form.querySelectorAll("label").forEach((label) => {
      const id = label.getAttribute("for");
      if (!id) return;
      const input = form.querySelector("#" + id);
      if (!input) return;
      if (!input.placeholder) {
        const text = (label.textContent || "").replace(/\s+/g, " ").trim();
        input.placeholder = text;
      }
      label.style.display = "none";
    });
  });
};

const autosizeSelect = (doc, win, select) => {
  if (!select) return;
  const selectedOption = select.options[select.selectedIndex];
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
    parseFloat(computed.paddingLeft || "0") + parseFloat(computed.paddingRight || "0") + 20;
  select.style.width = `${textWidth + horizontalPadding}px`;
};

const autosizeDashboardFilters = (doc, win) => {
  if (!doc || !win) return;
  const dashboardSelects = doc.querySelectorAll(".dashboard-filter-select");
  dashboardSelects.forEach((select) => {
    autosizeSelect(doc, win, select);
    select.addEventListener("change", () => autosizeSelect(doc, win, select));
  });
};

const initBaseInteractions = (win) => {
  const w = resolveWindow(win);
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
};

const autoInit = () => {
  if (!globalWindow || !globalWindow.document) return;
  setInitialTheme(globalWindow, globalWindow.document);
  const runInit = () => initBaseInteractions(globalWindow);
  if (globalWindow.document.readyState === "loading") {
    globalWindow.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { setInitialTheme, initBaseInteractions };
}

/* istanbul ignore next */
autoInit();
}
