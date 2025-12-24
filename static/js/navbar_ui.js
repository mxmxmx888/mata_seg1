(function (global) {
  function resetFloatingMenuStyles(menuEl, props) {
    if (!menuEl) return;
    (props || []).forEach((prop) => {
      menuEl.style.removeProperty(prop);
    });
  }

  function getDropdownOffset(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    const d = w ? w.document : typeof document !== "undefined" ? document : null;
    if (!d) return 18;
    const raw = w.getComputedStyle(d.documentElement).getPropertyValue("--navbar-dropdown-offset");
    const parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : 18;
  }

  function positionFloatingMenu({ trigger, menu, breakpoint = 640, margin = 12, maxWidth = 360, offset = 18, props }) {
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

  function initNavbar(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    const doc = w.document;
    const floatingMenuProps = ["position", "top", "left", "right", "transform", "width", "max-width"];

    const toggleBtn = doc.getElementById("prepTimeToggle");
    const popover = doc.getElementById("prepFilterPopover");

    if (toggleBtn && popover) {
      const positionPopover = () =>
        positionFloatingMenu({
          trigger: toggleBtn,
          menu: popover,
          breakpoint: 640,
          maxWidth: 360,
          offset: getDropdownOffset(w),
          props: floatingMenuProps
        });

      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const shouldOpen = !popover.classList.contains("prep-filter-open");
        popover.classList.toggle("prep-filter-open", shouldOpen);
        if (shouldOpen) {
          positionPopover();
        }
      });

      doc.addEventListener("click", (e) => {
        if (!popover.contains(e.target) && !toggleBtn.contains(e.target)) {
          popover.classList.remove("prep-filter-open");
        }
      });

      w.addEventListener("resize", () => {
        if (popover.classList.contains("prep-filter-open")) {
          positionPopover();
        }
      });
    }

    const notifDropdowns = Array.from(doc.querySelectorAll("#notificationDropdown, #notificationDropdownMobile"));
    if (notifDropdowns.length) {
      let markedRead = false;
      const trackedMenus = [];
      const dropdownOffset = getDropdownOffset(w);

      const updateAllNotificationMenus = () => {
        trackedMenus.forEach(({ trigger, menu }) =>
          positionFloatingMenu({
            trigger,
            menu,
            breakpoint: 590,
            maxWidth: 420,
            offset: dropdownOffset,
            props: floatingMenuProps
          })
        );
      };

      w.addEventListener("resize", updateAllNotificationMenus);

      const markRead = () => {
        if (markedRead) return;
        markedRead = true;
        w.fetch(doc.body.dataset.markNotificationsUrl || "", {
          method: "POST",
          headers: { "X-CSRFToken": doc.body.dataset.csrf || "" }
        }).catch(() => {});
      };

      const attachHandlers = (dropdownEl) => {
        const icon = dropdownEl.querySelector("i");
        const dropdownMenu = dropdownEl.closest(".dropdown")?.querySelector(".dropdown-menu");

        if (dropdownMenu) {
          trackedMenus.push({ trigger: dropdownEl, menu: dropdownMenu });
        }

        const fillHeart = () => {
          if (!icon) return;
          icon.classList.remove("bi-heart");
          icon.classList.add("bi-heart-fill");
        };

        const unfillHeart = () => {
          if (!icon) return;
          icon.classList.remove("bi-heart-fill");
          icon.classList.add("bi-heart");
        };

        const clearDot = () => {
          const dot = dropdownEl.querySelector(".notification-dot");
          if (dot && dot.parentNode) {
            dot.remove();
          }
        };

        const handleOpen = () => {
          clearDot();
          fillHeart();
          markRead();
          positionFloatingMenu({
            trigger: dropdownEl,
            menu: dropdownMenu,
            breakpoint: 590,
            maxWidth: 420,
            offset: dropdownOffset,
            props: floatingMenuProps
          });
        };

        const handleClose = () => {
          unfillHeart();
          positionFloatingMenu({
            trigger: dropdownEl,
            menu: dropdownMenu,
            breakpoint: 590,
            maxWidth: 420,
            offset: dropdownOffset,
            props: floatingMenuProps
          });
        };

        const syncFromState = () => {
          const isOpen = dropdownEl.getAttribute("aria-expanded") === "true" || (dropdownMenu && dropdownMenu.classList.contains("show"));
          if (isOpen) {
            handleOpen();
          } else {
            handleClose();
          }
        };

        dropdownEl.addEventListener("show.bs.dropdown", handleOpen);
        dropdownEl.addEventListener("shown.bs.dropdown", handleOpen);
        dropdownEl.addEventListener("hidden.bs.dropdown", handleClose);

        dropdownEl.addEventListener("click", () => {
          setTimeout(syncFromState, 0);
        });

        if (dropdownMenu && w.MutationObserver) {
          const observer = new w.MutationObserver(syncFromState);
          observer.observe(dropdownMenu, { attributes: true, attributeFilter: ["class"] });
        }
      };

      notifDropdowns.forEach(attachHandlers);
    }

    const searchInput = doc.querySelector(".recipi-nav-search-input");
    if (searchInput) {
      const recipeSuggestions = ["15 minute pasta", "one-pan chicken", "banana protein milkshake", "sheet-pan salmon", "chocolate protein oats"];

      const prefix = "Try ‘";
      const suffix = "’";
      const compactPlaceholder = "Search...";
      const fullSearchPlaceholder = "Search Recipi...";

      let placeholderIndex = 0;
      let charIndex = 0;
      let isDeleting = false;
      let typingTimeoutId = null;
      let animationActive = true;

      const isCompact = () => searchInput.clientWidth > 0 && searchInput.clientWidth < 260;
      const getSearchPlaceholder = () => (isCompact() ? compactPlaceholder : fullSearchPlaceholder);

      function updatePlaceholder(textFragment) {
        if (isCompact()) {
          searchInput.placeholder = compactPlaceholder;
          return;
        }
        const middle = textFragment || "";
        const closing = middle ? suffix : "";
        searchInput.placeholder = prefix + middle + closing;
      }

      function typePlaceholder() {
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
      }

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

    const appMenuToggle = doc.querySelector(".app-menu-toggle");
    const appFullScreenMenu = doc.getElementById("appFullScreenMenu");
    if (appMenuToggle && appFullScreenMenu) {
      const appMenuCloseBtn = doc.querySelector(".app-fullscreen-menu-close");

      const setMenuState = (shouldOpen) => {
        if (shouldOpen) {
          appFullScreenMenu.classList.add("is-open");
          appFullScreenMenu.setAttribute("aria-hidden", "false");
          appMenuToggle.classList.add("is-open");
          appMenuToggle.setAttribute("aria-expanded", "true");
          doc.body.classList.add("app-menu-open");
        } else {
          appFullScreenMenu.classList.remove("is-open");
          appFullScreenMenu.setAttribute("aria-hidden", "true");
          appMenuToggle.classList.remove("is-open");
          appMenuToggle.setAttribute("aria-expanded", "false");
          doc.body.classList.remove("app-menu-open");
        }
      };

      const toggleMenu = (shouldOpen) => {
        const isCurrentlyOpen = appFullScreenMenu.classList.contains("is-open");
        const nextState = typeof shouldOpen === "boolean" ? shouldOpen : !isCurrentlyOpen;
        setMenuState(nextState);
      };

      appMenuToggle.addEventListener("click", () => toggleMenu());

      appFullScreenMenu.addEventListener("click", (event) => {
        if (event.target === appFullScreenMenu) {
          toggleMenu(false);
        }
      });

      appFullScreenMenu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => toggleMenu(false));
      });

      if (appMenuCloseBtn) {
        appMenuCloseBtn.addEventListener("click", () => toggleMenu(false));
      }
    }
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
