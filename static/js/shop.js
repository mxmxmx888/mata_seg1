{
const globalWindow = typeof window !== "undefined" ? window : null;

const setManualScrollRestoration = (w) => {
  if (w && w.history && "scrollRestoration" in w.history) {
    w.history.scrollRestoration = "manual";
  }
};

const scrollToTop = (w, doc) => {
  if (!w || !doc) return;
  const isJsdom = Boolean(w.navigator && /jsdom/i.test(w.navigator.userAgent || ""));
  const applyScroll = () => {
    const scrollingEl = doc.scrollingElement || doc.documentElement || doc.body;
    if (scrollingEl) scrollingEl.scrollTop = 0;
    if (doc.body) doc.body.scrollTop = 0;
    if (!isJsdom && typeof w.scrollTo === "function") {
      w.scrollTo(0, 0);
    }
  };
  applyScroll();
  if (typeof w.requestAnimationFrame === "function") w.requestAnimationFrame(applyScroll);
  if (typeof w.setTimeout === "function") {
    w.setTimeout(applyScroll, 50);
    w.setTimeout(applyScroll, 200);
  }
};

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

function getColumnCount(w) {
  const width = w.innerWidth;
  for (const bp of breakpoints) {
    if (width >= bp.width) return bp.count;
  }
  return 2;
}

function createColumns(doc, container, count) {
  const cols = [];
  for (let i = 0; i < count; i += 1) {
    const col = doc.createElement("div");
    col.className = "shop-column";
    container.appendChild(col);
    cols.push(col);
  }
  return cols;
}

function shortestColumn(columns) {
  return columns.reduce((shortest, col) => (col.offsetHeight < shortest.offsetHeight ? col : shortest), columns[0]);
}

function placeItems(columns, nodes) {
  /* istanbul ignore next */
  if (!nodes || !nodes.length || !columns.length) return;
  nodes.forEach((node) => {
    const target = shortestColumn(columns);
    target.appendChild(node);
  });
}

function rebuildColumns(doc, container, columns, desiredCount, force) {
  const cards = Array.from(container.querySelectorAll(".shop-masonry-item"));
  if (!force && columns.length === desiredCount) return columns;
  container.innerHTML = "";
  const newColumns = createColumns(doc, container, desiredCount);
  placeItems(newColumns, cards);
  return newColumns;
}

function waitForImages(nodes) {
  const imgs = [];
  nodes.forEach((node) => {
    imgs.push(...node.querySelectorAll("img"));
  });
  /* istanbul ignore next */
  if (!imgs.length) return Promise.resolve();
  return new Promise((resolve) => {
    let done = 0;
    const finish = () => {
      done += 1;
      if (done >= imgs.length) resolve();
    };
    imgs.forEach((img) => {
      if (img.complete) {
        finish();
      } else {
        img.addEventListener("load", finish, { once: true });
        img.addEventListener("error", finish, { once: true });
      }
    });
  });
}

function createAppendHtml(doc, placeInColumns) {
  return (html) => {
    /* istanbul ignore next */
    if (!html) return Promise.resolve();
    const temp = doc.createElement("div");
    temp.innerHTML = html;
    const items = Array.from(temp.children);
    return Promise.resolve()
      .then(() => {
        placeInColumns(items);
        return waitForImages(items);
      })
      .then(() => {
        items.forEach((node) => {
          if (node.parentElement) node.remove();
        });
        placeInColumns(items);
      });
  };
}

function buildNextPageUrl(w, seed, page) {
  const nextPage = page + 1;
  const url = new URL(w.location.href);
  url.searchParams.set("page", String(nextPage));
  if (seed) url.searchParams.set("seed", seed);
  url.searchParams.set("ajax", "1");
  return { href: url.toString(), nextPage };
}

const fetchShopPage = (w, href) =>
  w.fetch(href, {
    headers: { "X-Requested-With": "XMLHttpRequest" }
  });

function shouldLoadFromScroll(doc, w) {
  const scrollPosition = w.innerHeight + w.scrollY;
  const threshold = doc.body.offsetHeight - 300;
  return scrollPosition >= threshold;
}

function buildShopContext(w) {
  const doc = w.document;
  const container = doc.getElementById("shop-items-container");
  const sentinel = doc.getElementById("shop-sentinel");
  if (!container || !sentinel) return null;
  return {
    w,
    doc,
    container,
    sentinel,
    loadingEl: doc.getElementById("shop-loading"),
    seed: container.dataset.seed || "",
    page: Number(container.dataset.page || "1"),
    hasNext: String(container.dataset.hasNext) === "true",
    columns: [],
    observer: null,
    loading: false
  };
}

const createRefreshColumns = (ctx) => (force = false) => {
  ctx.columns = rebuildColumns(ctx.doc, ctx.container, ctx.columns, getColumnCount(ctx.w), force);
};

const createSetLoading = (ctx) => (state) => {
  ctx.loading = state;
  if (!ctx.loadingEl) return;
  ctx.loadingEl.classList.toggle("d-none", !state);
};

function createApplyPageData(ctx, appendHtml) {
  return (data) =>
    appendHtml(data && data.html).then(() => {
      ctx.hasNext = Boolean(data && data.has_next);
      if (!ctx.hasNext && ctx.observer) {
        ctx.observer.disconnect();
      }
    });
}

function createLoadMore(ctx, setLoading, appendHtml) {
  const applyPageData = createApplyPageData(ctx, appendHtml);
  return () => {
    if (ctx.loading || !ctx.hasNext) return;
    setLoading(true);
    const { href, nextPage } = buildNextPageUrl(ctx.w, ctx.seed, ctx.page);
    return fetchShopPage(ctx.w, href)
      .then((response) => {
        if (!response.ok) throw new Error("Network response was not ok");
        return response.json();
      })
      .then((data) =>
        applyPageData(data).then(() => {
          ctx.page = nextPage;
        })
      )
      .catch(() => {})
      .finally(() => {
        setLoading(false);
      });
  };
}

function setupInitialLayout(ctx, refreshColumns) {
  const initialItems = Array.from(ctx.container.querySelectorAll(".shop-masonry-item"));
  refreshColumns();
  waitForImages(initialItems).then(() => refreshColumns(true));
}

function attachResize(ctx, refreshColumns) {
  ctx.w.addEventListener("resize", () => refreshColumns(true));
}

const createObserver = (ctx, loadMore) => {
  if (!("IntersectionObserver" in ctx.w)) return null;
  return new ctx.w.IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && loadMore()),
    { rootMargin: "600px 0px" }
  );
};

const createScrollFallback = (ctx, loadMore) => () => {
  if (ctx.loading || !ctx.hasNext) return;
  if (shouldLoadFromScroll(ctx.doc, ctx.w)) loadMore();
};

function attachInfinite(ctx, loadMore) {
  if (!ctx.hasNext) return;
  const observer = createObserver(ctx, loadMore);
  if (observer) {
    ctx.observer = observer;
    observer.observe(ctx.sentinel);
    return;
  }
  ctx.w.addEventListener("scroll", createScrollFallback(ctx, loadMore));
}

function initShop(win) {
  const w = resolveWindow(win);
  /* istanbul ignore next */
  if (!w || !w.document) return;
  setManualScrollRestoration(w);
  scrollToTop(w, w.document);

  const ctx = buildShopContext(w);
  /* istanbul ignore next */
  if (!ctx) return;

  const refreshColumns = createRefreshColumns(ctx);
  const setLoading = createSetLoading(ctx);
  const placeInColumns = (nodes) => placeItems(ctx.columns, nodes);
  const appendHtml = createAppendHtml(ctx.doc, placeInColumns);
  const loadMoreShopItems = createLoadMore(ctx, setLoading, appendHtml);

  setupInitialLayout(ctx, refreshColumns);
  attachResize(ctx, refreshColumns);
  attachInfinite(ctx, loadMoreShopItems);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { initShop };
}

/* istanbul ignore next */
if (globalWindow && globalWindow.document) {
  const runInit = () => initShop(globalWindow);
  if (globalWindow.document.readyState === "loading") {
    globalWindow.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
}
}
