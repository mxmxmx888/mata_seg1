(function (global) {
  const FLOATING_MENU_PROPS = ["position", "top", "left", "right", "transform", "width", "max-width"];
  const DEFAULT_DROPDOWN_MARGIN = 12;

  function resolveWindow(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    return w && w.document ? w : null;
  }

  function resetFloatingMenuStyles(menuEl, props) {
    if (!menuEl) return;
    (props || []).forEach((prop) => menuEl.style.removeProperty(prop));
  }

  function getDropdownOffset(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    const d = w ? w.document : typeof document !== "undefined" ? document : null;
    if (!d) return 18;
    const raw = w.getComputedStyle(d.documentElement).getPropertyValue("--navbar-dropdown-offset");
    const parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : 18;
  }

  function positionFloatingMenu({
    trigger,
    menu,
    breakpoint = 640,
    margin = DEFAULT_DROPDOWN_MARGIN,
    maxWidth = 360,
    offset = 18,
    props = FLOATING_MENU_PROPS,
  }) {
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
  }

  function initPrepFilter(w, doc) {
    const toggleBtn = doc.getElementById("prepTimeToggle");
    const popover = doc.getElementById("prepFilterPopover");
    if (!toggleBtn || !popover) return;
    const positionPopover = () =>
      positionFloatingMenu({
        trigger: toggleBtn,
        menu: popover,
        breakpoint: 640,
        maxWidth: 360,
        offset: getDropdownOffset(w),
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
  }

  function markNotificationsReadOnce(w, doc) {
    let marked = false;
    return () => {
      if (marked) return;
      marked = true;
      w.fetch(doc.body.dataset.markNotificationsUrl || "", {
        method: "POST",
        headers: { "X-CSRFToken": doc.body.dataset.csrf || "" },
      }).catch(() => {});
    };
  }

  function isDropdownOpen(dropdownEl, dropdownMenu) {
    return (
      dropdownEl.getAttribute("aria-expanded") === "true" ||
      (dropdownMenu && dropdownMenu.classList.contains("show"))
    );
  }

  function syncNotificationMenu(dropdownEl, dropdownMenu, dropdownOffset) {
    const isOpen = isDropdownOpen(dropdownEl, dropdownMenu);
    positionFloatingMenu({
      trigger: dropdownEl,
      menu: dropdownMenu,
      breakpoint: 590,
      maxWidth: 420,
      offset: dropdownOffset,
    });
    const icon = dropdownEl.querySelector("i");
    if (!icon) return;
    icon.classList.toggle("bi-heart-fill", isOpen);
    icon.classList.toggle("bi-heart", !isOpen);
  }

  function attachNotificationDropdown(w, doc, dropdownEl, dropdownOffset, trackedMenus, markRead) {
    const dropdownMenu = dropdownEl.closest(".dropdown")?.querySelector(".dropdown-menu");
    if (dropdownMenu) trackedMenus.push({ trigger: dropdownEl, menu: dropdownMenu });
    const clearDot = () => {
      const dot = dropdownEl.querySelector(".notification-dot");
      if (dot && dot.parentNode) dot.remove();
    };
    const handleOpen = () => {
      clearDot();
      markRead();
      syncNotificationMenu(dropdownEl, dropdownMenu, dropdownOffset);
    };
    const handleClose = () => syncNotificationMenu(dropdownEl, dropdownMenu, dropdownOffset);
    const syncFromState = () => syncNotificationMenu(dropdownEl, dropdownMenu, dropdownOffset);
    dropdownEl.addEventListener("show.bs.dropdown", handleOpen);
    dropdownEl.addEventListener("shown.bs.dropdown", handleOpen);
    dropdownEl.addEventListener("hidden.bs.dropdown", handleClose);
    dropdownEl.addEventListener("click", () =>
      setTimeout(() => {
        if (isDropdownOpen(dropdownEl, dropdownMenu)) {
          clearDot();
          markRead();
        }
        syncFromState();
      }, 0)
    );
    if (dropdownMenu && w.MutationObserver) {
      new w.MutationObserver(syncFromState).observe(dropdownMenu, { attributes: true, attributeFilter: ["class"] });
    }
  }

  function initNotificationDropdowns(w, doc) {
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
          offset: dropdownOffset,
        })
      );
    };
    w.addEventListener("resize", updateAll);
    dropdownEls.forEach((el) => attachNotificationDropdown(w, doc, el, dropdownOffset, trackedMenus, markRead));
  }

  function initSearchPlaceholder(w, doc) {
    const searchInput = doc.querySelector(".recipi-nav-search-input");
    if (!searchInput) return;
    const recipeSuggestions = ["15 minute pasta", "one-pan chicken", "banana protein milkshake", "sheet-pan salmon", "chocolate protein oats"];
    const compactPlaceholder = "Search...";
    const fullSearchPlaceholder = "Search Recipi...";
    const prefix = "Try ‘";
    const suffix = "’";
    let placeholderIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typingTimeoutId = null;
    let animationActive = true;
    const isCompact = () => searchInput.clientWidth > 0 && searchInput.clientWidth < 260;
    const getSearchPlaceholder = () => (isCompact() ? compactPlaceholder : fullSearchPlaceholder);
    const updatePlaceholder = (textFragment) => {
      if (isCompact()) {
        searchInput.placeholder = compactPlaceholder;
        return;
      }
      const middle = textFragment || "";
      const closing = middle ? suffix : "";
      searchInput.placeholder = prefix + middle + closing;
    };
    const typePlaceholder = () => {
      if (!animationActive) return;
      if (isCompact()) {
        searchInput.placeholder = compactPlaceholder;
        typingTimeoutId = setTimeout(typePlaceholder, 800);
        return;
      }
      if (doc.activeElement === searchInput || (searchInput.value && searchInput.value.trim() !== "")) {
        typingTimeoutId = setTimeout(typePlaceholder, 500);
        return;
      }
      const currentRecipe = recipeSuggestions[placeholderIndex];
      if (!isDeleting) {
        charIndex += 1;
        const visible = currentRecipe.slice(0, charIndex);
        updatePlaceholder(visible);
        if (charIndex === currentRecipe.length) {
          isDeleting = true;
          typingTimeoutId = setTimeout(typePlaceholder, 1500);
          return;
        }
      } else {
        charIndex -= 1;
        const visible = currentRecipe.slice(0, Math.max(charIndex, 0));
        updatePlaceholder(visible);
        if (charIndex <= 0) {
          isDeleting = false;
          placeholderIndex = (placeholderIndex + 1) % recipeSuggestions.length;
        }
      }
      const delay = isDeleting ? 40 : 80;
      typingTimeoutId = setTimeout(typePlaceholder, delay);
    };
    searchInput.addEventListener("focus", () => {
      animationActive = false;
      if (typingTimeoutId) {
        clearTimeout(typingTimeoutId);
        typingTimeoutId = null;
      }
      searchInput.placeholder = getSearchPlaceholder();
    });
    searchInput.addEventListener("blur", () => {
      if (searchInput.value && searchInput.value.trim() !== "") return;
      if (!animationActive) {
        animationActive = true;
        typePlaceholder();
      }
    });
    w.addEventListener("resize", () => {
      if (doc.activeElement === searchInput) {
        searchInput.placeholder = getSearchPlaceholder();
        return;
      }
      if (typingTimeoutId) {
        clearTimeout(typingTimeoutId);
        typingTimeoutId = null;
      }
      animationActive = true;
      charIndex = 0;
      isDeleting = false;
      updatePlaceholder("");
      typePlaceholder();
    });
    updatePlaceholder("");
    typePlaceholder();
  }

  function initAppFullScreenMenu(doc) {
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
  }

  function initNavbar(win) {
    const w = resolveWindow(win);
    if (!w) return;
    const doc = w.document;
    initPrepFilter(w, doc);
    initNotificationDropdowns(w, doc);
    initSearchPlaceholder(w, doc);
    initAppFullScreenMenu(doc);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initNavbar, getDropdownOffset, positionFloatingMenu, resetFloatingMenuStyles };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initNavbar(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
