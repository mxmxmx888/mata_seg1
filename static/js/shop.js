(function (global) {
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

  function initShop(win) {
    const w = resolveWindow(win);
    /* istanbul ignore next */
    if (!w || !w.document) return;

    const doc = w.document;
    const container = doc.getElementById("shop-items-container");
    const sentinel = doc.getElementById("shop-sentinel");
    const loadingEl = doc.getElementById("shop-loading");
    const seed = (container && container.dataset.seed) || "";
    /* istanbul ignore next */
    if (!container || !sentinel) return;

    let columns = [];
    const refreshColumns = (force = false) => {
      columns = rebuildColumns(doc, container, columns, getColumnCount(w), force);
    };
    const placeInColumns = (nodes) => placeItems(columns, nodes);

    let page = Number(container.dataset.page || "1");
    let loading = false;
    let hasNext = String(container.dataset.hasNext) === "true";
    let observer = null;

    const setLoading = (state) => {
      loading = state;
      if (!loadingEl) return;
      if (state) {
        loadingEl.classList.remove("d-none");
      } else {
        loadingEl.classList.add("d-none");
      }
    };

    const appendHtml = createAppendHtml(doc, placeInColumns);
    const applyPageData = (data) =>
      appendHtml(data && data.html).then(() => {
        hasNext = Boolean(data && data.has_next);
        if (!hasNext && observer) {
          observer.disconnect();
        }
      });

    const loadMoreShopItems = () => {
      if (loading || !hasNext) return;
      setLoading(true);
      const { href, nextPage } = buildNextPageUrl(w, seed, page);
      return fetchShopPage(w, href)
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) =>
          applyPageData(data).then(() => {
            page = nextPage;
          })
        )
        .catch(() => {})
        .finally(() => {
          setLoading(false);
        });
    };

    const initialItems = Array.from(container.querySelectorAll(".shop-masonry-item"));
    refreshColumns();
    waitForImages(initialItems).then(() => {
      refreshColumns(true);
    });
    w.addEventListener("resize", () => {
      refreshColumns(true);
    });

    if (hasNext) {
      observer =
        "IntersectionObserver" in w
          ? new w.IntersectionObserver(
              (entries) => {
                entries.forEach((entry) => {
                  if (entry.isIntersecting) {
                    loadMoreShopItems();
                  }
                });
              },
              { rootMargin: "600px 0px" }
            )
          : null;

      if (observer) {
        observer.observe(sentinel);
      } else {
        w.addEventListener("scroll", () => {
          if (loading || !hasNext) return;
          if (shouldLoadFromScroll(doc, w)) {
            loadMoreShopItems();
          }
        });
      }
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initShop };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initShop(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
