(function (global) {
  function initShop(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    /* istanbul ignore next */
    if (!w || !w.document) return;

    const doc = w.document;
    const container = doc.getElementById("shop-items-container");
    const sentinel = doc.getElementById("shop-sentinel");
    const loadingEl = doc.getElementById("shop-loading");
    const seed = (container && container.dataset.seed) || "";
    /* istanbul ignore next */
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
      const width = w.innerWidth;
      for (const bp of breakpoints) {
        if (width >= bp.width) return bp.count;
      }
      return 2;
    }

    let columns = [];

    function shortestColumn() {
      let target = columns[0];
      for (let i = 1; i < columns.length; i += 1) {
        if (columns[i].offsetHeight < target.offsetHeight) {
          target = columns[i];
        }
      }
      return target;
    }

    function placeItems(nodes) {
      /* istanbul ignore next */
      if (!nodes || !nodes.length) return;
      nodes.forEach((node) => {
        const target = shortestColumn();
        target.appendChild(node);
      });
    }

    function buildColumns(force) {
      const desiredCount = getColumnCount();
      const cards = Array.from(container.querySelectorAll(".shop-masonry-item"));
      if (!force && columns.length === desiredCount) return;

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

    let page = Number(container.dataset.page || "1");
    let loading = false;
    let hasNext = String(container.dataset.hasNext) === "true";

    function setLoading(state) {
      loading = state;
      if (!loadingEl) return;
      if (state) {
        loadingEl.classList.remove("d-none");
      } else {
        loadingEl.classList.add("d-none");
      }
    }

    function appendHtml(html) {
      /* istanbul ignore next */
      if (!html) return Promise.resolve();
      const temp = doc.createElement("div");
      temp.innerHTML = html;
      const items = Array.from(temp.children);
      return Promise.resolve().then(() => {
        placeItems(items);
        return waitForImages(items).then(() => {
          items.forEach((node) => {
            if (node.parentElement) node.remove();
          });
          placeItems(items);
        });
      });
    }

    const buildNextPageUrl = () => {
      const nextPage = page + 1;
      const url = new URL(w.location.href);
      url.searchParams.set("page", String(nextPage));
      if (seed) url.searchParams.set("seed", seed);
      url.searchParams.set("ajax", "1");
      return { href: url.toString(), nextPage };
    };

    const fetchShopPage = (href) =>
      w.fetch(href, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

    const applyPageData = (data) =>
      appendHtml(data && data.html).then(() => {
        hasNext = Boolean(data && data.has_next);
        if (!hasNext && observer) {
          observer.disconnect();
        }
      });

    function loadMoreShopItems() {
      if (loading || !hasNext) return;
      setLoading(true);
      const { href, nextPage } = buildNextPageUrl();
      return fetchShopPage(href)
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => applyPageData(data).then(() => {
          page = nextPage;
        }))
        .catch(() => {})
        .finally(() => {
          setLoading(false);
        });
    }

    const initialItems = Array.from(container.querySelectorAll(".shop-masonry-item"));
    buildColumns();
    waitForImages(initialItems).then(() => {
      buildColumns(true);
    });
    w.addEventListener("resize", () => {
      buildColumns(true);
    });

    if (hasNext) {
      const observer =
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
          const scrollPosition = w.innerHeight + w.scrollY;
          const threshold = doc.body.offsetHeight - 300;
          if (scrollPosition >= threshold) {
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
