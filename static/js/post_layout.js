(function (global) {
  function initPostLayout(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__postLayoutInitialized) return;
    w.__postLayoutInitialized = true;

    const doc = w.document;
    const primary = doc.getElementById("post-primary");
    const similar = doc.querySelector(".post-view-similar");
    const masonry = doc.querySelector(".post-media-masonry");
    const masonryItems = masonry ? Array.from(masonry.querySelectorAll(".post-media-masonry-item")) : [];

    const ensureMasonryCols = () => {
      if (!masonry) return [];
      let cols = Array.from(masonry.querySelectorAll(".post-media-masonry-col"));
      if (cols.length === 0) {
        const fragment = doc.createDocumentFragment();
        for (let i = 0; i < 2; i += 1) {
          const col = doc.createElement("div");
          col.className = "post-media-masonry-col";
          fragment.appendChild(col);
        }
        masonry.prepend(fragment);
        cols = Array.from(masonry.querySelectorAll(".post-media-masonry-col"));
      }
      return cols;
    };

    const buildMasonry = () => {
      if (!masonry || masonryItems.length === 0) return;
      const cols = ensureMasonryCols();
      if (cols.length === 0) return;
      const colCount = w.innerWidth <= 768 ? 1 : 2;
      masonry.style.gridTemplateColumns = `repeat(${colCount}, minmax(0, 1fr))`;
      const activeCols = cols.slice(0, colCount);
      cols.forEach((col, index) => {
        col.innerHTML = "";
        col.style.display = index < colCount ? "flex" : "none";
      });
      const heights = activeCols.map(() => 0);
      masonryItems.forEach((item) => {
        const media = item.querySelector("img, video");
        const rect = media && typeof media.getBoundingClientRect === "function"
          ? media.getBoundingClientRect()
          : typeof item.getBoundingClientRect === "function"
            ? item.getBoundingClientRect()
            : { height: 1 };
        const height = rect && rect.height ? rect.height : 1;
        const target = colCount === 1 ? 0 : (heights[0] <= heights[1] ? 0 : 1);
        activeCols[target].appendChild(item);
        heights[target] += height;
      });
    };

    const requestMasonry = () => w.requestAnimationFrame(buildMasonry);
    masonryItems.forEach((item) => {
      const media = item.querySelector("img, video");
      if (media) {
        if (media.complete) {
          requestMasonry();
        } else {
          media.addEventListener("load", requestMasonry, { once: true });
        }
      }
    });

    w.addEventListener("resize", requestMasonry);
    requestMasonry();

    const similarGrids = Array.from(doc.querySelectorAll(".view-similar-grid, .view-similar-grid-wide"));
    const baselineWidths = new Map();
    const setBaselines = () => {
      similarGrids.forEach((grid) => {
        const baseCols = grid.classList.contains("view-similar-grid-wide") ? 4 : 3;
        const width = grid.clientWidth || grid.offsetWidth;
        if (!width) return;
        baselineWidths.set(grid, width / baseCols);
      });
    };
    const updateSimilarColumns = () => {
      similarGrids.forEach((grid) => {
        const baseWidth = baselineWidths.get(grid);
        const width = grid.clientWidth || grid.offsetWidth;
        if (!baseWidth || !width) return;
        const cols = Math.max(1, Math.round(width / baseWidth));
        grid.style.setProperty("--similar-cols", cols);
      });
    };

    const handleScroll = () => {
      if (!primary || !similar) return;
      const rect = similar.getBoundingClientRect();
      const windowHeight = w.innerHeight || doc.documentElement.clientHeight;
      const fadeStart = windowHeight * 1.0;
      const fadeEnd = windowHeight * 0.4;
      const progress = Math.min(1, Math.max(0, (fadeStart - rect.top) / (fadeStart - fadeEnd)));
      primary.style.setProperty("--post-fade-amount", progress.toFixed(2));
    };

    w.addEventListener("scroll", handleScroll);
    w.addEventListener("resize", updateSimilarColumns);
    w.addEventListener("resize", handleScroll);

    setBaselines();
    updateSimilarColumns();

    const backButton = doc.querySelector(".post-back-button");
    const parseUrl = (value) => {
      if (!value) return null;
      try {
        return new URL(value, w.location.href);
      } catch (error) {
        return null;
      }
    };

    const cameFromCreate = (() => {
      const parsed = parseUrl(doc.referrer);
      if (!parsed) return false;
      return /\/recipes\/create\/?$/i.test(parsed.pathname);
    })();

    if (cameFromCreate && w.history) {
      if (typeof w.history.replaceState === "function") {
        w.history.replaceState(null, "", w.location.href);
      }
      if (typeof w.history.pushState === "function") {
        w.history.pushState({ preventReturnToCreate: true }, "", w.location.href);
        w.addEventListener("popstate", () => {
          const fallbackHref = backButton ? backButton.dataset.fallback || "/" : "/";
          w.location.replace(fallbackHref);
        }, { once: true });
      }
    }

    const resolveBackTarget = () => {
      if (!backButton) return { target: null, referrer: null, fallback: null };
      const fallbackHref = backButton.dataset.fallback || backButton.getAttribute("href") || "/";
      const refValue = cameFromCreate ? "" : (backButton.dataset.entry || doc.referrer || "");
      const parsedRef = parseUrl(refValue);
      const isSameOrigin = parsedRef && parsedRef.origin === w.location.origin && parsedRef.href !== w.location.href;
      const target = isSameOrigin ? parsedRef.href : fallbackHref;
      backButton.setAttribute("href", target);
      return {
        target,
        referrer: isSameOrigin ? parsedRef.href : null,
        fallback: fallbackHref
      };
    };

    const backState = resolveBackTarget();
    if (backButton) {
      backButton.addEventListener("click", (event) => {
        const hasHistory = w.history.length > 1 && backState.referrer;
        if (hasHistory) {
          event.preventDefault();
          w.history.back();
          return;
        }
        if (backState.referrer && backState.target === backState.referrer) {
          event.preventDefault();
          w.location.assign(backState.referrer);
        }
      });
    }

    const lightbox = doc.getElementById("lightbox");
    const triggerBack = () => {
      const fallbackHref = backButton
        ? (backButton.dataset.fallback || backButton.getAttribute("href") || "/")
        : "/";
      const hasHistory = w.history.length > 1;
      if (hasHistory) {
        w.history.back();
        return;
      }
      w.location.assign(fallbackHref);
    };

    doc.addEventListener("keyup", (event) => {
      if (event.key !== "Escape") return;
      const modalOpen = doc.querySelector(".modal.show");
      const lightboxOpen = lightbox && !lightbox.classList.contains("d-none");
      if (modalOpen || lightboxOpen) return;
      triggerBack();
    });

    const likeForm = doc.querySelector("[data-like-form]");
    if (likeForm) {
      const likeButton = likeForm.querySelector("[data-like-toggle]");
      const likeIcon = likeButton ? likeButton.querySelector("i") : null;
      const likeCountEl = likeForm.querySelector("[data-like-count]");
      const csrfInput = likeForm.querySelector("input[name=csrfmiddlewaretoken]")
        || doc.querySelector("input[name=csrfmiddlewaretoken]");
      const csrfToken = csrfInput ? csrfInput.value : "";

      const setLikeState = (liked, count) => {
        if (!likeButton || !likeIcon) return;
        likeButton.dataset.liked = liked ? "true" : "false";
        likeButton.setAttribute("aria-pressed", liked ? "true" : "false");
        likeIcon.classList.toggle("bi-heart-fill", liked);
        likeIcon.classList.toggle("bi-heart", !liked);
        likeButton.classList.toggle("is-liked", liked);
        if (likeCountEl && typeof count === "number" && !Number.isNaN(count)) {
          likeCountEl.textContent = Math.max(0, count);
        }
      };

      const parseCount = () => {
        if (!likeCountEl) return 0;
        const parsed = parseInt(likeCountEl.textContent, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
      };

      likeForm.addEventListener("submit", (event) => {
        if (!likeButton || !likeIcon || !csrfToken || typeof w.fetch === "undefined") return;
        event.preventDefault();
        const wasLiked = likeButton.dataset.liked === "true";
        const nextCount = wasLiked ? parseCount() - 1 : parseCount() + 1;
        likeButton.disabled = true;

        w
          .fetch(likeForm.action, {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
              "X-CSRFToken": csrfToken,
              "X-Requested-With": "XMLHttpRequest"
            },
            body: ""
          })
          .then((resp) => {
            if (resp && resp.ok) {
              setLikeState(!wasLiked, nextCount);
              return;
            }
            likeForm.submit();
          })
          .catch(() => likeForm.submit())
          .finally(() => {
            likeButton.disabled = false;
          });
      });
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initPostLayout };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initPostLayout(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
