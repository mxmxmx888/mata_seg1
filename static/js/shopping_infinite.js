(function (global) {
  function initShoppingInfinite(win) {
    // Sets up responsive infinite scroll for the Shop grid (#shopping-grid + .shop-masonry-item cards).
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__shoppingInfiniteInitialized) return;
    w.__shoppingInfiniteInitialized = true;

    const doc = w.document;
    const container = doc.getElementById("shopping-grid");
    const sentinel = doc.getElementById("shopping-sentinel");
    const loadingEl = doc.getElementById("shopping-loading");
    if (!container || !sentinel) return;

    const breakpoints = [
      { width: 1600, count: 6 },
      { width: 1400, count: 5 },
      { width: 1200, count: 4 },
      { width: 992, count: 3 },
      { width: 768, count: 3 },
      { width: 520, count: 2 },
      { width: 0, count: 2 }
    ];

    function getColumnCount() {
      const wWidth = w.innerWidth;
      for (let i = 0; i < breakpoints.length; i += 1) {
        if (wWidth >= breakpoints[i].width) return breakpoints[i].count;
      }
      return 2;
    }

    let columns = [];

    function placeItems(nodes) {
      if (!nodes || !nodes.length) return;
      nodes.forEach((node) => {
        let target = columns[0];
        for (let i = 1; i < columns.length; i += 1) {
          if (columns[i].offsetHeight < target.offsetHeight) {
            target = columns[i];
          }
        }
        target.appendChild(node);
      });
    }

    function buildColumns() {
      const desiredCount = getColumnCount();
      if (columns.length === desiredCount) return;

      const cards = Array.from(container.querySelectorAll(".shop-masonry-item"));
      container.innerHTML = "";
      columns = [];
      for (let i = 0; i < desiredCount; i += 1) {
        const col = doc.createElement("div");
        col.className = "shop-column";
        container.appendChild(col);
        columns.push(col);
      }
      placeItems(cards);
    }

    let page = Number(container.dataset.page || "1");
    let hasNext = (container.dataset.shoppingHasNext || "true") === "true";
    const infinite = w.InfiniteList || {};

    function setLoading(state) {
      if (!loadingEl) return;
      loadingEl.classList.toggle("d-none", !state);
    }

    const placeNodes = (nodes) => {
      if (!nodes || !nodes.length) return;
      if (typeof infinite.placeInColumns === "function") {
        infinite.placeInColumns(nodes, columns);
        return;
      }
      placeItems(nodes);
    };

    function appendHtml(html) {
      if (!html) return;
      const temp = doc.createElement("div");
      temp.innerHTML = html;
      const items = Array.from(temp.children);
      placeNodes(items);
    }

    if (!infinite.create) {
      buildColumns();
      return;
    }

    const buildNextPageUrl = (targetPage) => {
      const url = new URL(w.location.href);
      url.searchParams.set("page", String(targetPage));
      url.searchParams.set("ajax", "1");
      return url.toString();
    };

    const fetchPage = ({ page: targetPage }) => {
      setLoading(true);
      return w
        .fetch(buildNextPageUrl(targetPage), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data && data.html) appendHtml(data.html);
          const more = Boolean(data && data.has_next);
          if (more) {
            page = targetPage;
          }
          return {
            html: "",
            hasMore: more,
            nextPage: more ? targetPage + 1 : null,
          };
        })
        .finally(() => setLoading(false));
    };

    infinite.create({
      sentinel,
      hasMore: hasNext,
      nextPage: hasNext ? page + 1 : null,
      fetchPage,
      append: () => {},
      observerOptions: { rootMargin: "600px 0px" },
      fallbackScroll: true,
      fallbackMargin: 300,
    });

    buildColumns();
    w.addEventListener("resize", buildColumns);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initShoppingInfinite };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initShoppingInfinite(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
