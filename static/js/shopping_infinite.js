(function (global) {
  function initShoppingInfinite(win) {
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
    let loading = false;
    let hasNext = (container.dataset.shoppingHasNext || "true") === "true";

    function setLoading(state) {
      loading = state;
      if (!loadingEl) return;
      loadingEl.classList.toggle("d-none", !state);
    }

    function appendHtml(html) {
      if (!html) return;
      const temp = doc.createElement("div");
      temp.innerHTML = html;
      const items = Array.from(temp.children);
      placeItems(items);
    }

    function loadMoreShopping() {
      if (loading || !hasNext) return;
      setLoading(true);

      page += 1;
      const url = new URL(w.location.href);
      url.searchParams.set("page", String(page));
      url.searchParams.set("ajax", "1");

      w
        .fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data && data.html) appendHtml(data.html);
          hasNext = Boolean(data && data.has_next);
          if (!hasNext && observer) observer.disconnect();
          setLoading(false);
        })
        .catch(() => {
          page -= 1;
          setLoading(false);
        });
    }

    const observer = "IntersectionObserver" in w
      ? new w.IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              loadMoreShopping();
            }
          });
        }, { rootMargin: "600px 0px" })
      : null;

    if (observer) {
      observer.observe(sentinel);
    } else {
      w.addEventListener("scroll", () => {
        if (loading || !hasNext) return;
        const scrollPosition = w.innerHeight + w.scrollY;
        const threshold = doc.body.offsetHeight - 300;
        if (scrollPosition >= threshold) {
          loadMoreShopping();
        }
      });
    }

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
