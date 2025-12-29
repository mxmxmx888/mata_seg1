(() => {
const FLOATING_MENU_PROPS = ["position", "top", "left", "right", "transform", "width", "max-width"];
const DEFAULT_DROPDOWN_MARGIN = 12;
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const resetFloatingMenuStyles = (menuEl, props = FLOATING_MENU_PROPS) => {
  if (!menuEl) return;
  props.forEach((prop) => menuEl.style.removeProperty(prop));
};

const getDropdownOffset = (win) => {
  const w = win || globalWindow;
  const d = w ? w.document : null;
  if (!d) return 18;
  const raw = w.getComputedStyle(d.documentElement).getPropertyValue("--navbar-dropdown-offset");
  const parsed = parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : 18;
};

const positionFloatingMenu = ({ trigger, menu, breakpoint = 640, margin = DEFAULT_DROPDOWN_MARGIN, maxWidth = 360, offset = 18, props = FLOATING_MENU_PROPS }) => {
  if (!trigger || !menu) return;
  const w = trigger.ownerDocument.defaultView;
  if (w.innerWidth > breakpoint) {
    resetFloatingMenuStyles(menu, props);
    return;
  }
  const computedMaxWidth = Math.min(maxWidth, w.innerWidth - margin * 2);
  const left = Math.max(margin, (w.innerWidth - computedMaxWidth) / 2);
  const triggerRect = trigger.getBoundingClientRect();
  const top = Math.max(margin, triggerRect.bottom + offset);
  menu.style.setProperty("position", "fixed", "important");
  menu.style.setProperty("top", `${top}px`, "important");
  menu.style.setProperty("left", `${left}px`, "important");
  menu.style.setProperty("right", "auto", "important");
  menu.style.setProperty("transform", "none", "important");
  menu.style.setProperty("width", `${computedMaxWidth}px`, "important");
  menu.style.setProperty("max-width", `${w.innerWidth - margin * 2}px`, "important");
};

const initPrepFilter = (w, doc) => {
  const toggleBtn = doc.getElementById("prepTimeToggle");
  const popover = doc.getElementById("prepFilterPopover");
  if (!toggleBtn || !popover) return;
  const positionPopover = () =>
    positionFloatingMenu({
      trigger: toggleBtn,
      menu: popover,
      breakpoint: 640,
      maxWidth: 360,
      offset: getDropdownOffset(w)
    });
  toggleBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    const shouldOpen = !popover.classList.contains("prep-filter-open");
    popover.classList.toggle("prep-filter-open", shouldOpen);
    if (shouldOpen) positionPopover();
  });
  doc.addEventListener("click", (event) => {
    if (!popover.contains(event.target) && !toggleBtn.contains(event.target)) {
      popover.classList.remove("prep-filter-open");
    }
  });
  w.addEventListener("resize", () => {
    if (popover.classList.contains("prep-filter-open")) positionPopover();
  });
};

const markNotificationsReadOnce = (w, doc) => {
  let marked = false;
  return () => {
    if (marked) return;
    marked = true;
    w
      .fetch(doc.body.dataset.markNotificationsUrl || "", {
        method: "POST",
        headers: { "X-CSRFToken": doc.body.dataset.csrf || "" }
      })
      .catch(() => {});
  };
};

const isDropdownOpen = (dropdownEl, dropdownMenu) =>
  dropdownEl.getAttribute("aria-expanded") === "true" || (dropdownMenu && dropdownMenu.classList.contains("show"));

const syncNotificationMenu = (dropdownEl, dropdownMenu, dropdownOffset) => {
  const isOpen = isDropdownOpen(dropdownEl, dropdownMenu);
  positionFloatingMenu({
    trigger: dropdownEl,
    menu: dropdownMenu,
    breakpoint: 590,
    maxWidth: 420,
    offset: dropdownOffset
  });
  const icon = dropdownEl.querySelector("i");
  if (!icon) return;
  icon.classList.toggle("bi-heart-fill", isOpen);
  icon.classList.toggle("bi-heart", !isOpen);
};

const clearNotificationDot = (dropdownEl) => {
  const dot = dropdownEl.querySelector(".notification-dot");
  if (dot && dot.parentNode) dot.remove();
};

const bindNotificationEvents = (w, dropdownEl, dropdownMenu, dropdownOffset, markRead) => {
  const sync = () => syncNotificationMenu(dropdownEl, dropdownMenu, dropdownOffset);
  const handleOpen = () => {
    clearNotificationDot(dropdownEl);
    markRead();
    sync();
  };
  const handleClick = () =>
    setTimeout(() => {
      if (isDropdownOpen(dropdownEl, dropdownMenu)) {
        clearNotificationDot(dropdownEl);
        markRead();
      }
      sync();
    }, 0);
  dropdownEl.addEventListener("show.bs.dropdown", handleOpen);
  dropdownEl.addEventListener("shown.bs.dropdown", handleOpen);
  dropdownEl.addEventListener("hidden.bs.dropdown", sync);
  dropdownEl.addEventListener("click", handleClick);
  if (dropdownMenu && w.MutationObserver) {
    new w.MutationObserver(sync).observe(dropdownMenu, { attributes: true, attributeFilter: ["class"] });
  }
};

const attachNotificationDropdown = (w, doc, dropdownEl, dropdownOffset, trackedMenus, markRead) => {
  const dropdownMenu = dropdownEl.closest(".dropdown")?.querySelector(".dropdown-menu");
  if (dropdownMenu) trackedMenus.push({ trigger: dropdownEl, menu: dropdownMenu });
  bindNotificationEvents(w, dropdownEl, dropdownMenu, dropdownOffset, markRead);
};

const initNotificationDropdowns = (w, doc) => {
  const dropdownEls = Array.from(doc.querySelectorAll("#notificationDropdown, #notificationDropdownMobile"));
  if (!dropdownEls.length) return;
  const trackedMenus = [];
  const dropdownOffset = getDropdownOffset(w);
  const markRead = markNotificationsReadOnce(w, doc);
  const updateAll = () => {
    trackedMenus.forEach(({ trigger, menu }) =>
      positionFloatingMenu({
        trigger,
        menu,
        breakpoint: 590,
        maxWidth: 420,
        offset: dropdownOffset
      })
    );
  };
  w.addEventListener("resize", updateAll);
  dropdownEls.forEach((el) => attachNotificationDropdown(w, doc, el, dropdownOffset, trackedMenus, markRead));
};

const buildSearchState = (w, doc, input) => ({
  w,
  doc,
  input,
  suggestions: ["15 minute pasta", "one-pan chicken", "banana protein milkshake", "sheet-pan salmon", "chocolate protein oats"],
  compactText: "Search...",
  fullText: "Search Recipi...",
   focusText: "Search...",
  prefix: "Try ‘",
  suffix: "’",
  placeholderIndex: 0,
  charIndex: 0,
  isDeleting: false,
  animationActive: true,
  timeoutId: null
});

const isCompactSearch = (state) => state.input.clientWidth > 0 && state.input.clientWidth < 260;

const setPlaceholderText = (state, fragment) => {
  if (isCompactSearch(state)) {
    state.input.placeholder = state.compactText;
    return;
  }
  const middle = fragment || "";
  const closing = middle ? state.suffix : "";
  state.input.placeholder = state.prefix + middle + closing;
};

const clearTypingTimeout = (state) => {
  if (state.timeoutId) {
    clearTimeout(state.timeoutId);
    state.timeoutId = null;
  }
};

const pauseForUser = (state) => {
  if (state.doc.activeElement === state.input) return true;
  const hasValue = state.input.value && state.input.value.trim() !== "";
  return hasValue;
};

const advancePlaceholderState = (state, recipe) => {
  if (!state.isDeleting) {
    state.charIndex += 1;
    const visible = recipe.slice(0, state.charIndex);
    setPlaceholderText(state, visible);
    if (state.charIndex >= recipe.length) {
      state.isDeleting = true;
      return 1500;
    }
  } else {
    state.charIndex -= 1;
    const visible = recipe.slice(0, Math.max(state.charIndex, 0));
    setPlaceholderText(state, visible);
    if (state.charIndex <= 0) {
      state.isDeleting = false;
      state.placeholderIndex = (state.placeholderIndex + 1) % state.suggestions.length;
    }
  }
  return state.isDeleting ? 40 : 80;
};

const typePlaceholder = (state) => {
  if (!state.animationActive) return;
  if (isCompactSearch(state)) {
    setPlaceholderText(state, "");
    state.timeoutId = setTimeout(() => typePlaceholder(state), 800);
    return;
  }
  if (pauseForUser(state)) {
    state.timeoutId = setTimeout(() => typePlaceholder(state), 500);
    return;
  }
  const recipe = state.suggestions[state.placeholderIndex];
  const delay = advancePlaceholderState(state, recipe);
  state.timeoutId = setTimeout(() => typePlaceholder(state), delay);
};

const onSearchFocus = (state) => {
  state.animationActive = false;
  clearTypingTimeout(state);
  state.input.placeholder = state.focusText;
};

const onSearchBlur = (state) => {
  if (state.input.value && state.input.value.trim() !== "") return;
  if (!state.animationActive) {
    state.animationActive = true;
    typePlaceholder(state);
  }
};

const onSearchResize = (state) => {
  if (state.doc.activeElement === state.input) {
    setPlaceholderText(state, "");
    return;
  }
  clearTypingTimeout(state);
  state.animationActive = true;
  state.charIndex = 0;
  state.isDeleting = false;
  setPlaceholderText(state, "");
  typePlaceholder(state);
};

const wireSearchPlaceholder = (state) => {
  state.input.addEventListener("focus", () => onSearchFocus(state));
  state.input.addEventListener("blur", () => onSearchBlur(state));
  state.w.addEventListener("resize", () => onSearchResize(state));
  setPlaceholderText(state, "");
  typePlaceholder(state);
};

const initSearchPlaceholder = (w, doc) => {
  const searchInput = doc.querySelector(".recipi-nav-search-input");
  if (!searchInput) return;
  const state = buildSearchState(w, doc, searchInput);
  wireSearchPlaceholder(state);
};

const initAppFullScreenMenu = (doc) => {
  const toggle = doc.querySelector(".app-menu-toggle");
  const menu = doc.getElementById("appFullScreenMenu");
  if (!toggle || !menu) return;
  const closeBtn = doc.querySelector(".app-fullscreen-menu-close");
  const setMenuState = (shouldOpen) => {
    menu.classList.toggle("is-open", shouldOpen);
    menu.setAttribute("aria-hidden", shouldOpen ? "false" : "true");
    toggle.classList.toggle("is-open", shouldOpen);
    toggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
    doc.body.classList.toggle("app-menu-open", shouldOpen);
  };
  const toggleMenu = (shouldOpen) => {
    const nextState = typeof shouldOpen === "boolean" ? shouldOpen : !menu.classList.contains("is-open");
    setMenuState(nextState);
  };
  toggle.addEventListener("click", () => toggleMenu());
  menu.addEventListener("click", (event) => {
    if (event.target === menu) toggleMenu(false);
  });
  menu.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => toggleMenu(false)));
  if (closeBtn) closeBtn.addEventListener("click", () => toggleMenu(false));
};

const initNavbar = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document) return;
  const doc = w.document;
  initPrepFilter(w, doc);
  initNotificationDropdowns(w, doc);
  initSearchPlaceholder(w, doc);
  initAppFullScreenMenu(doc);
};

const autoInitNavbar = () => {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initNavbar(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initNavbar, getDropdownOffset, positionFloatingMenu, resetFloatingMenuStyles };
}

/* istanbul ignore next */
autoInitNavbar();
})();
