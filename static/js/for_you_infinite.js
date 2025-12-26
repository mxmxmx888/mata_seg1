(function (global) {
  function initForYouInfinite(win) {
    // Sets up infinite scroll for the For You grid (#forYou-grid + .feed-masonry-column items).
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__forYouInfiniteInitialized) return;
    w.__forYouInfiniteInitialized = true;

    const doc = w.document;
    const container = doc.getElementById("forYou-grid");
    const sentinel = doc.getElementById("forYou-sentinel");
    const loadingEl = doc.getElementById("forYou-loading");
    if (!container || !sentinel) return;

    const columns = Array.from(container.querySelectorAll(".feed-masonry-column"));
    if (!columns.length) return;

    const LIMIT = 12;
    let offset = container.querySelectorAll(".my-recipe-card").length;
    const initialHasMore = offset >= LIMIT;
    const infinite = w.InfiniteList || {};

    function setLoading(state) {
      if (!loadingEl) return;
      loadingEl.classList.toggle("d-none", !state);
    }

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

    const fetchPage = ({ page }) => {
      setLoading(true);
      const url = new URL(w.location.href);
      url.searchParams.set("for_you_ajax", "1");
      url.searchParams.set("for_you_offset", String(page));

      return w
        .fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          const count = (data && data.count) || 0;
          offset = page + count;
          return {
            html: (data && data.html) || "",
            hasMore: Boolean(data && data.has_more),
            nextPage: count ? page + count : null,
          };
        })
        .finally(() => setLoading(false));
    };

    infinite.create({
      sentinel,
      hasMore: initialHasMore,
      nextPage: initialHasMore ? offset : null,
      fetchPage,
      append: appendHtmlToColumns,
      observerOptions: { rootMargin: "600px 0px" },
      fallbackScroll: true,
      fallbackMargin: 300,
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initForYouInfinite };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initForYouInfinite(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
