{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const resolveWindow = (win) => win || globalWindow;
const markInitialized = (w, flag) => {
  if (!w || w[flag]) return false;
  w[flag] = true;
  return true;
};

const placeCards = (cards, infinite, columns, state) => {
  if (!cards || !cards.length) return;
  if (typeof infinite.placeInColumns === "function") {
    infinite.placeInColumns(cards, columns);
    return;
  }
  cards.forEach((card) => {
    const idx = state && columns.length ? state.nextColumn % columns.length : 0;
    const target = columns[idx] || columns[0];
    target.appendChild(card);
    if (state) state.nextColumn = (idx + 1) % columns.length;
  });
};

const appendHtmlToColumns = (doc, infinite, columns, state) => (html) => {
  if (!html) return;
  const temp = doc.createElement("div");
  temp.innerHTML = html;
  const cards = Array.from(temp.querySelectorAll(".my-recipe-card"));
  placeCards(cards, infinite, columns, state);
};

const setLoading = (loadingEl, state) => {
  if (!loadingEl) return;
  loadingEl.classList.toggle("d-none", !state);
};

const fetchPageFactory = (w, state, loadingEl) => ({ page }) => {
  setLoading(loadingEl, true);
  const url = new URL(w.location.href);
  url.searchParams.set("for_you_ajax", "1");
  url.searchParams.set("for_you_offset", String(page));
  return w
    .fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then((resp) => {
      if (!resp.ok) throw new Error("Network response was not ok");
      return resp.json();
    })
    .then((data) => {
      const count = (data && data.count) || 0;
      state.offset = page + count;
      return {
        html: (data && data.html) || "",
        hasMore: Boolean(data && data.has_more),
        nextPage: count ? page + count : null,
      };
    })
    .finally(() => setLoading(loadingEl, false));
};

const gatherForYouContext = (w) => {
  const doc = w.document;
  const container = doc.getElementById("forYou-grid");
  const sentinel = doc.getElementById("forYou-sentinel");
  const loadingEl = doc.getElementById("forYou-loading");
  if (!container || !sentinel) return null;
  const columns = Array.from(container.querySelectorAll(".feed-masonry-column"));
  if (!columns.length) return null;
  const LIMIT = 12;
  const initialCards = container.querySelectorAll(".my-recipe-card").length;
  const state = { offset: initialCards, nextColumn: initialCards % (columns.length || 1) };
  return {
    doc,
    sentinel,
    loadingEl,
    columns,
    state,
    initialHasMore: initialCards >= LIMIT,
    infinite: w.InfiniteList || {},
  };
};

const initForYouInfinite = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || !markInitialized(w, "__forYouInfiniteInitialized")) return;
  const ctx = gatherForYouContext(w);
  if (!ctx || !ctx.infinite.create) return;
  ctx.infinite.create({
    sentinel: ctx.sentinel,
    hasMore: ctx.initialHasMore,
    nextPage: ctx.initialHasMore ? ctx.state.offset : null,
    fetchPage: fetchPageFactory(w, ctx.state, ctx.loadingEl),
    append: appendHtmlToColumns(ctx.doc, ctx.infinite, ctx.columns, ctx.state),
    columns: ctx.columns,
    observerOptions: { rootMargin: "1200px 0px" },
    fallbackScroll: true,
    fallbackMargin: 600,
    fallbackMode: "document",
  });
};

const autoInit = () => {
  const w = resolveWindow();
  if (!w || !w.document) return;
  const runInit = () => initForYouInfinite(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initForYouInfinite };
}

/* istanbul ignore next */
autoInit();
}
