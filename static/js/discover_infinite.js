(function (global) {
  function initDiscoverInfinite(win) {
    // Sets up infinite scroll for the Discover grid (#discover-grid + .feed-masonry-column items).
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__discoverInfiniteInitialized) return;
    w.__discoverInfiniteInitialized = true;

    const doc = w.document;
    const container = doc.getElementById("discover-grid");
    if (!container) return;

    const columns = Array.from(container.querySelectorAll(".feed-masonry-column"));
    if (!columns.length) return;

    const existingSentinel = doc.getElementById("discover-sentinel");
    const sentinel = existingSentinel || (() => {
      const s = doc.createElement("div");
      s.id = "discover-sentinel";
      s.className = "infinite-sentinel";
      const parent = container.parentNode;
      if (parent) {
        parent.appendChild(s);
      } else {
        doc.body.appendChild(s);
      }
      return s;
    })();

    let page = Number(container.dataset.page || "1");
    const hasNext = (container.dataset.popularHasNext || "true") === "true";
    const infinite = w.InfiniteList || {};

    const placeCards = (cards) => {
      if (!cards || !cards.length) return;
      if (typeof infinite.placeInColumns === "function") {
        infinite.placeInColumns(cards, columns);
        return;
      }
      cards.forEach((card) => {
        let target = columns[0];
        for (let i = 1; i < columns.length; i += 1) {
          if (columns[i].offsetHeight < target.offsetHeight) {
            target = columns[i];
          }
        }
        target.appendChild(card);
      });
    };

    function appendHtmlToColumns(html) {
      if (!html) return;
      const temp = doc.createElement("div");
      temp.innerHTML = html;
      const cards = Array.from(temp.querySelectorAll(".my-recipe-card"));
      placeCards(cards);
    }

    if (!infinite.create) return;

    const fetchPage = ({ page: targetPage }) => {
      const url = new URL(w.location.href);
      url.searchParams.set("page", String(targetPage));
      url.searchParams.set("ajax", "1");

      return w
        .fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network error");
          return response.json();
        })
        .then((data) => {
          page = targetPage;
          const more = Boolean(data && data.has_next);
          return {
            html: (data && data.html) || "",
            hasMore: more,
            nextPage: more ? targetPage + 1 : null,
          };
        })
        .catch(() => ({ html: "", hasMore: true, nextPage: targetPage }));
    };

    infinite.create({
      sentinel,
      hasMore: hasNext,
      nextPage: hasNext ? page + 1 : null,
      fetchPage,
      append: appendHtmlToColumns,
      fallbackScroll: true,
      fallbackMargin: 300,
      fallbackMode: "document",
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initDiscoverInfinite };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initDiscoverInfinite(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
