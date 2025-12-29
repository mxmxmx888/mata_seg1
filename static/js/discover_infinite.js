{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const resolveWindow = (win) => win || globalWindow;
const markInitialized = (w, flag) => {
  if (!w || w[flag]) return false;
  w[flag] = true;
  return true;
};

const ensureSentinel = (doc, container) => {
  const existing = doc.getElementById("discover-sentinel");
  if (existing) return existing;
  const s = doc.createElement("div");
  s.id = "discover-sentinel";
  s.className = "infinite-sentinel";
  (container.parentNode || doc.body).appendChild(s);
  return s;
};

const placeCards = (cards, infinite, columns) => {
  if (!cards || !cards.length) return;
  if (typeof infinite.placeInColumns === "function") {
    infinite.placeInColumns(cards, columns);
    return;
  }
  cards.forEach((card) => {
    let target = columns[0];
    for (let i = 1; i < columns.length; i += 1) {
      if (columns[i].offsetHeight < target.offsetHeight) target = columns[i];
    }
    target.appendChild(card);
  });
};

const appendHtmlToColumns = (doc, infinite, columns) => (html) => {
  if (!html) return;
  const temp = doc.createElement("div");
  temp.innerHTML = html;
  const cards = Array.from(temp.querySelectorAll(".my-recipe-card"));
  placeCards(cards, infinite, columns);
};

const fetchPageFactory = (w, state) => ({ page: targetPage }) => {
  const url = new URL(w.location.href);
  url.searchParams.set("page", String(targetPage));
  url.searchParams.set("ajax", "1");
  return w
    .fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then((resp) => {
      if (!resp.ok) throw new Error("Network error");
      return resp.json();
    })
    .then((data) => {
      state.page = targetPage;
      const more = Boolean(data && data.has_next);
      return { html: (data && data.html) || "", hasMore: more, nextPage: more ? targetPage + 1 : null };
    })
    .catch(() => ({ html: "", hasMore: true, nextPage: targetPage }));
};

const initDiscoverInfinite = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || !markInitialized(w, "__discoverInfiniteInitialized")) return;
  const doc = w.document;
  const container = doc.getElementById("discover-grid");
  if (!container) return;
  const columns = Array.from(container.querySelectorAll(".feed-masonry-column"));
  if (!columns.length) return;
  const sentinel = ensureSentinel(doc, container);
  const state = { page: Number(container.dataset.page || "1") };
  const hasNext = (container.dataset.popularHasNext || "true") === "true";
  const infinite = w.InfiniteList || {};
  if (!infinite.create) return;
  infinite.create({
    sentinel,
    hasMore: hasNext,
    nextPage: hasNext ? state.page + 1 : null,
    fetchPage: fetchPageFactory(w, state),
    append: appendHtmlToColumns(doc, infinite, columns),
    fallbackScroll: true,
    fallbackMargin: 300,
    fallbackMode: "document",
  });
};

const autoInit = () => {
  const w = resolveWindow();
  if (!w || !w.document) return;
  const runInit = () => initDiscoverInfinite(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initDiscoverInfinite };
}

/* istanbul ignore next */
autoInit();
}
