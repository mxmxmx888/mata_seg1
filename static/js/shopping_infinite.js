{
const globalWindow = typeof window !== "undefined" ? window : null;

const breakpoints = [
  { width: 1600, count: 6 },
  { width: 1400, count: 5 },
  { width: 1200, count: 4 },
  { width: 992, count: 3 },
  { width: 768, count: 3 },
  { width: 520, count: 2 },
  { width: 0, count: 2 }
];

const resolveWindow = (win) => win || (typeof window !== "undefined" ? window : undefined);

const getColumnCount = (w) => {
  const wWidth = w.innerWidth;
  for (let i = 0; i < breakpoints.length; i += 1) {
    if (wWidth >= breakpoints[i].width) return breakpoints[i].count;
  }
  return 2;
};

const createColumns = (doc, container, count) => {
  const cols = [];
  for (let i = 0; i < count; i += 1) {
    const col = doc.createElement("div");
    col.className = "shop-column";
    container.appendChild(col);
    cols.push(col);
  }
  return cols;
};

const shortestColumn = (columns) =>
  columns.reduce((target, col) => (col.offsetHeight < target.offsetHeight ? col : target), columns[0]);

const placeItems = (columns, nodes) => {
  if (!nodes || !nodes.length || !columns.length) return;
  nodes.forEach((node) => {
    const target = shortestColumn(columns);
    target.appendChild(node);
  });
};

const rebuildColumns = (doc, container, columns, desiredCount) => {
  if (columns.length === desiredCount) return columns;
  const cards = Array.from(container.querySelectorAll(".shop-masonry-item"));
  container.innerHTML = "";
  const newColumns = createColumns(doc, container, desiredCount);
  placeItems(newColumns, cards);
  return newColumns;
};

const createPlaceNodes = (infinite, getColumns) => (nodes) => {
  if (!nodes || !nodes.length) return;
  const cols = getColumns();
  if (typeof infinite.placeInColumns === "function") {
    infinite.placeInColumns(nodes, cols);
    return;
  }
  placeItems(cols, nodes);
};

const appendHtmlFactory = (doc, placeNodes) => (html) => {
  if (!html) return;
  const temp = doc.createElement("div");
  temp.innerHTML = html;
  const items = Array.from(temp.children);
  placeNodes(items);
};

const buildNextPageUrl = (w, targetPage) => {
  const url = new URL(w.location.href);
  url.searchParams.set("page", String(targetPage));
  url.searchParams.set("ajax", "1");
  return url.toString();
};

const fetchShoppingPage = (w, url) =>
  w.fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" }
  });

const setManualScrollRestoration = (w) => {
  if (w && w.history && "scrollRestoration" in w.history) {
    w.history.scrollRestoration = "manual";
  }
};

const scrollToTop = (w, doc, isJsdom) => {
  const applyScroll = () => {
    const scrollingEl = doc.scrollingElement || doc.documentElement || doc.body;
    if (scrollingEl) scrollingEl.scrollTop = 0;
    if (doc.body) doc.body.scrollTop = 0;
    if (!isJsdom && typeof w.scrollTo === "function") {
      w.scrollTo(0, 0);
    }
  };
  applyScroll();
  if (typeof w.requestAnimationFrame === "function") {
    w.requestAnimationFrame(applyScroll);
  }
  if (typeof w.setTimeout === "function") {
    w.setTimeout(applyScroll, 50);
    w.setTimeout(applyScroll, 200);
  }
};

const hookScrollResetEvents = (w, doc, isJsdom) => {
  if (!w || !doc || typeof w.addEventListener !== "function") return;
  const handler = () => scrollToTop(w, doc, isJsdom);
  w.addEventListener("pageshow", handler);
  w.addEventListener("load", handler);
};

const buildShoppingContext = (w) => {
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
    page: Number(container.dataset.page || "1"),
    hasNext: (container.dataset.shoppingHasNext || "true") === "true",
    infinite: w.InfiniteList || {},
    columns: []
  };
};

const createRefreshColumns = (ctx) => () => {
  ctx.columns = rebuildColumns(ctx.doc, ctx.container, ctx.columns, getColumnCount(ctx.w));
};

const createSetLoading = (ctx) => (state) => {
  if (!ctx.loadingEl) return;
  ctx.loadingEl.classList.toggle("d-none", !state);
};

const createFetchPage = (ctx, setLoading, appendHtml) => ({ page }) => {
  setLoading(true);
  return fetchShoppingPage(ctx.w, buildNextPageUrl(ctx.w, page))
    .then((response) => {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.json();
    })
    .then((data) => {
      if (data && data.html) appendHtml(data.html);
      const more = Boolean(data && data.has_next);
      if (more) {
        ctx.page = page;
      }
      return { html: "", hasMore: more, nextPage: more ? page + 1 : null };
    })
    .finally(() => setLoading(false));
};

const buildInfiniteConfig = (ctx, appendHtml, setLoading) => ({
  sentinel: ctx.sentinel,
  hasMore: ctx.hasNext,
  nextPage: ctx.hasNext ? ctx.page + 1 : null,
  fetchPage: createFetchPage(ctx, setLoading, appendHtml),
  append: () => {},
  observerOptions: { rootMargin: "600px 0px" },
  fallbackScroll: true,
  fallbackMargin: 300,
});

function wireShoppingGrid(ctx) {
  const refreshColumns = createRefreshColumns(ctx);
  const setLoading = createSetLoading(ctx);
  const placeNodes = createPlaceNodes(ctx.infinite, () => ctx.columns);
  const appendHtml = appendHtmlFactory(ctx.doc, placeNodes);

  if (!ctx.infinite.create) {
    refreshColumns();
    ctx.w.addEventListener("resize", refreshColumns);
    return;
  }

  ctx.infinite.create(buildInfiniteConfig(ctx, appendHtml, setLoading));

  refreshColumns();
  ctx.w.addEventListener("resize", refreshColumns);
}

function initShoppingInfinite(win) {
  // Sets up responsive infinite scroll for the Shop grid (#shopping-grid + .shop-masonry-item cards).
  const w = resolveWindow(win);
  if (!w || !w.document || w.__shoppingInfiniteInitialized) return;
  w.__shoppingInfiniteInitialized = true;
  setManualScrollRestoration(w);
  const isJsdom = Boolean(w.navigator && /jsdom/i.test(w.navigator.userAgent || ""));
  scrollToTop(w, w.document, isJsdom);
  hookScrollResetEvents(w, w.document, isJsdom);

  const ctx = buildShoppingContext(w);
  if (!ctx) return;
  wireShoppingGrid(ctx);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { initShoppingInfinite };
}

/* istanbul ignore next */
if (globalWindow && globalWindow.document) {
  const runInit = () => initShoppingInfinite(globalWindow);
  if (globalWindow.document.readyState === "loading") {
    globalWindow.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
}
}
