const globalWindow = typeof window !== "undefined" ? window : null;

const SHOP_INFINITE_BREAKPOINTS = [
  { width: 1600, count: 6 },
  { width: 1400, count: 5 },
  { width: 1200, count: 4 },
  { width: 992, count: 3 },
  { width: 768, count: 3 },
  { width: 520, count: 2 },
  { width: 0, count: 2 }
];

const columnsForWidth = (w) => {
  const width = w.innerWidth;
  for (const bp of SHOP_INFINITE_BREAKPOINTS) {
    if (width >= bp.width) return bp.count;
  }
  return 2;
};

const rebuildColumns = (state) => {
  const desired = columnsForWidth(state.w);
  if (state.columns.length === desired) return;
  const cards = Array.from(state.container.querySelectorAll(".shop-masonry-item"));
  state.container.innerHTML = "";
  state.columns = [];
  for (let i = 0; i < desired; i += 1) {
    const col = state.doc.createElement("div");
    col.className = "shop-column";
    state.container.appendChild(col);
    state.columns.push(col);
  }
  placeItems(state.columns, cards);
};

const placeItems = (columns, nodes) => {
  if (!nodes || !nodes.length) return;
  nodes.forEach((node, idx) => {
    const target = columns[idx % columns.length];
    target.appendChild(node);
  });
};

const setLoading = (state, isLoading) => {
  if (!state.loadingEl) return;
  state.loadingEl.classList.toggle("d-none", !isLoading);
};

const appendHtml = (state, html) => {
  if (!html) return;
  const temp = state.doc.createElement("div");
  temp.innerHTML = html;
  const items = Array.from(temp.children);
  if (typeof state.infinite.placeInColumns === "function") {
    state.infinite.placeInColumns(items, state.columns);
  } else {
    placeItems(state.columns, items);
  }
};

const fetchPage = async (state, targetPage) => {
  setLoading(state, true);
  const url = new URL(state.w.location.href);
  url.searchParams.set("page", String(targetPage));
  url.searchParams.set("ajax", "1");
  try {
    const response = await state.w.fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!response.ok) throw new Error("Network response was not ok");
    const data = await response.json();
    if (data && data.html) appendHtml(state, data.html);
    const more = Boolean(data && data.has_next);
    if (more) state.page = targetPage;
    return { html: "", hasMore: more, nextPage: more ? targetPage + 1 : null };
  } finally {
    setLoading(state, false);
  }
};

const buildShoppingState = (w) => {
  if (!w || !w.document || w.__shoppingInfiniteInitialized) return null;
  w.__shoppingInfiniteInitialized = true;
  const doc = w.document;
  const container = doc.getElementById("shopping-grid");
  const sentinel = doc.getElementById("shopping-sentinel");
  if (!container || !sentinel) return null;
  return {
    w,
    doc,
    container,
    sentinel,
    loadingEl: doc.getElementById("shopping-loading"),
    columns: [],
    page: Number(container.dataset.page || "1"),
    hasNext: (container.dataset.shoppingHasNext || "true") === "true",
    infinite: w.InfiniteList || {},
  };
};

const startShoppingInfinite = (state) => {
  rebuildColumns(state);
  if (!state.infinite.create) return;
  state.infinite.create({
    sentinel: state.sentinel,
    hasMore: state.hasNext,
    nextPage: state.hasNext ? state.page + 1 : null,
    fetchPage: ({ page }) => fetchPage(state, page),
    append: () => {},
    observerOptions: { rootMargin: "600px 0px" },
    fallbackScroll: true,
    fallbackMargin: 300,
  });
  state.w.addEventListener("resize", () => rebuildColumns(state));
};

const initShoppingInfinite = (win) => {
  const state = buildShoppingState(win || globalWindow);
  if (!state) return;
  startShoppingInfinite(state);
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { initShoppingInfinite };
}

/* istanbul ignore next */
const autoInitShoppingInfinite = () => {
  const w = globalWindow;
  if (!w || !w.document) return;
  const runInit = () => initShoppingInfinite(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

autoInitShoppingInfinite();
