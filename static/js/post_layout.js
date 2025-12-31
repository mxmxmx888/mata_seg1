{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;
const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};
const markInitialized = (w, flag) => {
  if (!w) return false;
  if (w[flag]) return false;
  w[flag] = true;
  return true;
};

const ensureMasonryColumns = (doc, masonry) => {
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
const resetMasonryColumns = (cols, colCount) => {
  cols.forEach((col, index) => {
    col.innerHTML = "";
    col.style.display = index < colCount ? "flex" : "none";
  });
};
const measureHeight = (el) => {
  const rect = el && typeof el.getBoundingClientRect === "function" ? el.getBoundingClientRect() : null;
  return rect && rect.height ? rect.height : 1;
};
const createMasonryRequester = (w, masonry, items) => {
  let layoutPending = false;
  const runLayout = () => {
    layoutPending = false;
    buildMasonry(w, masonry, items);
  };
  return () => {
    if (layoutPending) return;
    layoutPending = true;
    if (typeof w.requestAnimationFrame === "function") {
      w.requestAnimationFrame(runLayout);
    } else {
      w.setTimeout(runLayout, 0);
    }
  };
};
const attachMasonryMediaHandlers = (items, requestLayout) => {
  items.forEach((item) => {
    const media = item.querySelector("img, video");
    if (!media) return;
    if (media.complete) {
      requestLayout();
    } else {
      media.addEventListener("load", requestLayout, { once: true });
      media.addEventListener("error", requestLayout, { once: true });
    }
  });
};
const placeItemsInColumns = (items, activeCols) => {
  if (!items.length || !activeCols.length) return;
  const heights = activeCols.map((col) => col.offsetHeight || 0);
  const measuredHeights = items.map((item) => {
    const media = item.querySelector("img, video");
    return measureHeight(media || item);
  });
  items.forEach((item, index) => {
    let target = 0;
    for (let i = 1; i < heights.length; i += 1) {
      if (heights[i] < heights[target]) target = i;
    }
    activeCols[target].appendChild(item);
    heights[target] += measuredHeights[index] || 1;
  });
};
const buildMasonry = (w, masonry, items) => {
  if (!masonry || items.length === 0) return;
  const cols = ensureMasonryColumns(masonry.ownerDocument, masonry);
  if (cols.length === 0) return;
  const colCount = items.length === 1 ? 1 : w.innerWidth <= 768 ? 1 : 2;
  masonry.style.gridTemplateColumns = `repeat(${colCount}, minmax(0, 1fr))`;
  const activeCols = cols.slice(0, colCount);
  resetMasonryColumns(cols, colCount);
  placeItemsInColumns(items, activeCols);
};
const setupMasonry = (w, masonry) => {
  if (!masonry) return;
  const items = Array.from(masonry.querySelectorAll(".post-media-masonry-item"));
  const requestLayout = createMasonryRequester(w, masonry, items);
  attachMasonryMediaHandlers(items, requestLayout);
  w.addEventListener("resize", requestLayout);
  if (typeof w.ResizeObserver === "function") {
    const ro = new w.ResizeObserver(() => requestLayout());
    ro.observe(masonry);
  }
  requestLayout();
};

const getSimilarGrids = (doc) => Array.from(doc.querySelectorAll(".view-similar-grid, .view-similar-grid-wide"));
const setSimilarBaselines = (grids, baselines) => {
  grids.forEach((grid) => {
    const baseCols = grid.classList.contains("view-similar-grid-wide") ? 4 : 3;
    const width = grid.clientWidth || grid.offsetWidth;
    if (width) {
      baselines.set(grid, width / baseCols);
    }
  });
};
const updateSimilarColumns = (w, grids, baselines) => {
  grids.forEach((grid) => {
    const baseWidth = baselines.get(grid);
    const width = grid.clientWidth || grid.offsetWidth;
    if (!baseWidth || !width) return;
    const cols = Math.max(1, Math.round(width / baseWidth));
    grid.style.setProperty("--similar-cols", cols);
  });
};
const setupSimilarGrid = (w, doc) => {
  const grids = getSimilarGrids(doc);
  const baselines = new Map();
  const applyColumns = () => updateSimilarColumns(w, grids, baselines);
  setSimilarBaselines(grids, baselines);
  applyColumns();
  w.addEventListener("resize", applyColumns);
};

const updateFadeAmount = (w, primary, similar) => {
  if (!primary || !similar) return;
  const rect = similar.getBoundingClientRect();
  const windowHeight = w.innerHeight || primary.ownerDocument.documentElement.clientHeight;
  const fadeStart = windowHeight * 1.0;
  const fadeEnd = windowHeight * 0.4;
  const progress = Math.min(1, Math.max(0, (fadeStart - rect.top) / (fadeStart - fadeEnd)));
  primary.style.setProperty("--post-fade-amount", progress.toFixed(2));
};
const setupScrollFade = (w, primary, similar) => {
  if (!primary || !similar) return;
  const handler = () => updateFadeAmount(w, primary, similar);
  w.addEventListener("scroll", handler);
  w.addEventListener("resize", handler);
  handler();
};

const parseUrl = (w, value) => {
  if (!value) return null;
  try {
    return new URL(value, w.location.href);
  } catch (error) {
    return null;
  }
};
const isActionReferrer = (w, value) => {
  const parsed = parseUrl(w, value);
  if (!parsed) return false;
  return /\/comment\/?$/i.test(parsed.pathname);
};
const cameFromCreate = (w, doc) => {
  const parsed = parseUrl(w, doc.referrer);
  return parsed ? /\/recipes\/create\/?$/i.test(parsed.pathname) : false;
};
const cameFromEdit = (w, doc) => {
  const parsed = parseUrl(w, doc.referrer);
  const fromQuery = new URL(w.location.href).searchParams.has("from_edit");
  const fromPath = parsed && /\/recipes\/\d+\/edit\/?$/i.test(parsed.pathname);
  return fromQuery || fromPath;
};

const storeEntry = (w, postId, entry) => {
  if (!postId || !entry) return;
  try {
    w.sessionStorage.setItem(`post-entry-${postId}`, entry);
  } catch (err) {
    /* ignore */
  }
};
const getStoredEntry = (w, postId) => {
  if (!postId) return null;
  try {
    return w.sessionStorage.getItem(`post-entry-${postId}`);
  } catch (err) {
    return null;
  }
};
const resolveBackTarget = (w, doc, backButton, preventReturn) => {
  if (!backButton) return { target: null, referrer: null, fallback: "/" };
  const fallbackHref = backButton.dataset.fallback || backButton.getAttribute("href") || "/";
  const currentHref = w.location.href;
  const postId = backButton.dataset.postId || "";
  const entryCandidate = backButton.dataset.entry || doc.referrer || "";
  const storedEntryRaw = getStoredEntry(w, postId);
  const storedEntry = storedEntryRaw && storedEntryRaw !== currentHref ? storedEntryRaw : "";
  const useStoredEntry = isActionReferrer(w, entryCandidate);
  if (!preventReturn && entryCandidate && !useStoredEntry && !storedEntry) {
    storeEntry(w, postId, entryCandidate);
  }
  const refValue = preventReturn
    ? storedEntry || ""
    : useStoredEntry
      ? storedEntry || ""
      : entryCandidate || storedEntry || "";
  const parsedRef = parseUrl(w, refValue);
  const isSameOrigin = parsedRef && parsedRef.origin === w.location.origin && parsedRef.href !== currentHref;
  const targetCandidate = isSameOrigin ? parsedRef.href : fallbackHref;
  const target = targetCandidate && targetCandidate !== currentHref ? targetCandidate : fallbackHref;
  backButton.setAttribute("href", target);
  return { target, fallback: fallbackHref, storedEntry, useStoredEntry };
};
const applyPreventReturnGuards = (w, preventReturn, backButton) => {
  if (!preventReturn || !w.history) return;
  if (typeof w.history.replaceState === "function") {
    w.history.replaceState(null, "", w.location.href);
  }
  if (typeof w.history.pushState === "function") {
    w.history.pushState({ preventReturnToCreate: true }, "", w.location.href);
    w.addEventListener(
      "popstate",
      () => {
        const fallbackHref = backButton ? backButton.dataset.fallback || "/" : "/";
        w.location.replace(fallbackHref);
      },
      { once: true }
    );
  }
};

const updateBackHintVisibility = (w, doc) => {
  const backButton = doc.querySelector(".post-back-button");
  const gallery = doc.querySelector(".recipe-gallery");
  if (!backButton || !gallery || !backButton.getBoundingClientRect || !gallery.getBoundingClientRect) return;
  const backRect = backButton.getBoundingClientRect();
  const galleryRect = gallery.getBoundingClientRect();
  const verticalOverlap = backRect.bottom > galleryRect.top && backRect.top < galleryRect.bottom;
  const leftOfGallery = backRect.right <= galleryRect.left - 8;
  const shouldHide = !(verticalOverlap && leftOfGallery);
  backButton.classList.toggle("post-back-button--hide-hint", shouldHide);
};
const setupBackHintVisibility = (w, doc) => {
  const run = () => updateBackHintVisibility(w, doc);
  const requestRun = () => {
    if (typeof w.requestAnimationFrame === "function") {
      w.requestAnimationFrame(run);
    } else {
      run();
    }
  };
  run();
  w.addEventListener("resize", requestRun);
  w.addEventListener("load", requestRun, { once: true });
  const gallery = doc.querySelector(".recipe-gallery");
  if (gallery && typeof w.ResizeObserver === "function") {
    const ro = new w.ResizeObserver(() => requestRun());
    ro.observe(gallery);
  }
};
const triggerBack = (w, doc, backButton, preventReturn) => {
  const backState = resolveBackTarget(w, doc, backButton, preventReturn);
  const fallbackHref = backState.fallback || backState.target || "/";
  const currentHref = w.location.href;
  const destination = [backState.storedEntry, backState.target, fallbackHref].find(
    (href) => href && href !== currentHref
  ) || fallbackHref;
  const shouldBypassHistory =
    preventReturn || backState.useStoredEntry || !!backState.storedEntry || destination === fallbackHref;
  const hasHistory = w.history && w.history.length > 1 && !shouldBypassHistory;
  if (shouldBypassHistory || !hasHistory) {
    w.location.assign(destination);
    return;
  }
  w.history.back();
};
const setupBackNavigation = (w, doc) => {
  const backButton = doc.querySelector(".post-back-button");
  const preventReturn = cameFromCreate(w, doc) || cameFromEdit(w, doc);
  applyPreventReturnGuards(w, preventReturn, backButton);
  resolveBackTarget(w, doc, backButton, preventReturn);
  const handleEscape = (event) => {
    const key = (event.key || "").toLowerCase();
    const keyCode = typeof event.keyCode === "number" ? event.keyCode : event.which;
    const isEscape = key === "escape" || key === "esc" || keyCode === 27;
    if (!isEscape) return;
    triggerBack(w, doc, backButton, preventReturn);
  };
  if (backButton) {
    backButton.addEventListener("click", (event) => {
      event.preventDefault();
      triggerBack(w, doc, backButton, preventReturn);
    });
  }
  doc.addEventListener("keydown", handleEscape, true);
};

const getCsrfToken = (doc, form) => {
  const csrfInput = form.querySelector("input[name=csrfmiddlewaretoken]") || doc.querySelector("input[name=csrfmiddlewaretoken]");
  return csrfInput ? csrfInput.value : "";
};
const setLikeState = (likeButton, likeIcon, likeCountEl, liked, count) => {
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
const parseLikeCount = (likeCountEl) => {
  if (!likeCountEl) return 0;
  const parsed = parseInt(likeCountEl.textContent, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};
const submitLike = (w, form, csrfToken) =>
  w.fetch(form.action, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": csrfToken,
      "X-Requested-With": "XMLHttpRequest"
    },
    body: ""
  });
const handleLikeSubmit = (w, likeForm, likeButton, likeIcon, likeCountEl, csrfToken) => (event) => {
  if (!likeButton || !likeIcon || !csrfToken || typeof w.fetch === "undefined") return;
  event.preventDefault();
  const wasLiked = likeButton.dataset.liked === "true";
  const nextCount = wasLiked ? parseLikeCount(likeCountEl) - 1 : parseLikeCount(likeCountEl) + 1;
  likeButton.disabled = true;
  submitLike(w, likeForm, csrfToken)
    .then((resp) => {
      if (resp && resp.ok) {
        setLikeState(likeButton, likeIcon, likeCountEl, !wasLiked, nextCount);
        return;
      }
      likeForm.submit();
    })
    .catch(() => likeForm.submit())
    .finally(() => {
      likeButton.disabled = false;
    });
};
const wireLikeForm = (w, doc) => {
  const likeForm = doc.querySelector("[data-like-form]");
  if (!likeForm) return;
  const likeButton = likeForm.querySelector("[data-like-toggle]");
  const likeIcon = likeButton ? likeButton.querySelector("i") : null;
  const likeCountEl = likeForm.querySelector("[data-like-count]");
  const csrfToken = getCsrfToken(doc, likeForm);
  likeForm.addEventListener("submit", handleLikeSubmit(w, likeForm, likeButton, likeIcon, likeCountEl, csrfToken));
};

const initPostLayout = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || !markInitialized(w, "__postLayoutInitialized")) return;
  const doc = w.document;
  setupMasonry(w, doc.querySelector(".post-media-masonry"));
  setupSimilarGrid(w, doc);
  setupScrollFade(w, doc.getElementById("post-primary"), doc.querySelector(".post-view-similar"));
  setupBackNavigation(w, doc);
  setupBackHintVisibility(w, doc);
  wireLikeForm(w, doc);
};
const autoInitPostLayout = () => {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initPostLayout(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};
if (hasModuleExports) {
  module.exports = { initPostLayout };
}
/* istanbul ignore next */
autoInitPostLayout();
}
