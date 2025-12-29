const globalWindow = typeof window !== "undefined" ? window : null;

const SHOP_BREAKPOINTS = [
  { width: 1600, count: 6 },
  { width: 1400, count: 5 },
  { width: 1200, count: 4 },
  { width: 992, count: 3 },
  { width: 768, count: 3 },
  { width: 520, count: 2 },
  { width: 0, count: 2 }
];

const getColumnCount = (w) => {
  const width = w.innerWidth;
  for (const bp of SHOP_BREAKPOINTS) {
    if (width >= bp.width) return bp.count;
  }
  return 2;
};

const createColumns = (doc, container, count) => {
  container.innerHTML = "";
  const cols = [];
  for (let i = 0; i < count; i += 1) {
    const col = doc.createElement("div");
    col.className = "shop-column";
    container.appendChild(col);
    cols.push(col);
  }
  return cols;
};

const shortestColumn = (columns) => {
  let target = columns[0];
  for (let i = 1; i < columns.length; i += 1) {
    if (columns[i].offsetHeight < target.offsetHeight) {
      target = columns[i];
    }
  }
  return target;
};

const placeItems = (columns, nodes) => {
  if (!nodes || !nodes.length) return;
  nodes.forEach((node) => {
    const target = shortestColumn(columns);
    target.appendChild(node);
  });
};

const waitForImages = (w, nodes) => {
  const imgs = [];
  nodes.forEach((node) => imgs.push(...node.querySelectorAll("img")));
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
};

const appendHtml = async (state, html) => {
  if (!html) return;
  const temp = state.doc.createElement("div");
  temp.innerHTML = html;
  const items = Array.from(temp.children);
  placeItems(state.columns, items);
  await waitForImages(state.w, items);
  items.forEach((node) => {
    if (node.parentElement) node.remove();
  });
  placeItems(state.columns, items);
};

const setLoading = (state, isLoading) => {
  state.loading = isLoading;
  if (state.loadingEl) {
    state.loadingEl.classList.toggle("d-none", !isLoading);
  }
};

const buildColumns = (state, force = false) => {
  const desiredCount = getColumnCount(state.w);
  if (!force && state.columns.length === desiredCount) return;
  const cards = Array.from(state.container.querySelectorAll(".shop-masonry-item"));
  state.columns = createColumns(state.doc, state.container, desiredCount);
  placeItems(state.columns, cards);
};

const buildNextUrl = (state) => {
  const url = new URL(state.w.location.href);
  url.searchParams.set("page", String(state.page));
  if (state.seed) url.searchParams.set("seed", state.seed);
  url.searchParams.set("ajax", "1");
  return url.toString();
};

const loadMoreShopItems = async (state) => {
  if (state.loading || !state.hasNext) return;
  setLoading(state, true);
  state.page += 1;
  try {
    const response = await state.w.fetch(buildNextUrl(state), {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!response.ok) throw new Error("Network response was not ok");
    const data = await response.json();
    await appendHtml(state, data && data.html);
    state.hasNext = Boolean(data && data.has_next);
    if (!state.hasNext && state.observer) {
      state.observer.disconnect();
    }
  } catch (err) {
    state.page -= 1;
  } finally {
    setLoading(state, false);
  }
};

const attachObserver = (state) => {
  if (!state.hasNext) return null;
  if ("IntersectionObserver" in state.w) {
    const observer = new state.w.IntersectionObserver(
      (entries) => entries.forEach((entry) => entry.isIntersecting && loadMoreShopItems(state)),
      { rootMargin: "600px 0px" }
    );
    observer.observe(state.sentinel);
    return observer;
  }
  state.scrollHandler = () => {
    if (state.loading || !state.hasNext) return;
    const scrollPosition = state.w.innerHeight + state.w.scrollY;
    const threshold = state.doc.body.offsetHeight - 300;
    if (scrollPosition >= threshold) loadMoreShopItems(state);
  };
  state.w.addEventListener("scroll", state.scrollHandler);
  return null;
};

const buildShopState = (win) => {
  if (!win || !win.document) return null;
  const doc = win.document;
  const container = doc.getElementById("shop-items-container");
  const sentinel = doc.getElementById("shop-sentinel");
  const loadingEl = doc.getElementById("shop-loading");
  if (!container || !sentinel) return null;
  return {
    w: win,
    doc,
    container,
    sentinel,
    loadingEl,
    seed: (container && container.dataset.seed) || "",
    columns: [],
    page: Number(container.dataset.page || "1"),
    loading: false,
    hasNext: String(container.dataset.hasNext) === "true",
    observer: null,
    scrollHandler: null,
  };
};

function initShop(win) {
  const state = buildShopState(win || globalWindow);
  if (!state) return;
  buildColumns(state, true);
  const initialItems = Array.from(state.container.querySelectorAll(".shop-masonry-item"));
  waitForImages(state.w, initialItems).then(() => buildColumns(state, true));
  state.w.addEventListener("resize", () => buildColumns(state, true));
  state.observer = attachObserver(state);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { initShop };
}

/* istanbul ignore next */
const autoInitShop = () => {
  const w = globalWindow;
  if (!w || !w.document) return;
  const runInit = () => initShop(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

autoInitShop();
