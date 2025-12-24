(function (global) {
  function initDiscoverInfinite(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__discoverInfiniteInitialized) return;
    w.__discoverInfiniteInitialized = true;

    const doc = w.document;
    const container = doc.getElementById("discover-grid");
    if (!container) return;

    const columns = Array.from(container.querySelectorAll(".feed-masonry-column"));
    if (!columns.length) return;

    let page = Number(container.dataset.page || "1");
    let loading = false;
    let hasNext = (container.dataset.popularHasNext || "true") === "true";

    function appendHtmlToColumns(html) {
      if (!html) return;
      const temp = doc.createElement("div");
      temp.innerHTML = html;
      const cards = Array.from(temp.querySelectorAll(".my-recipe-card"));

      cards.forEach((card) => {
        let target = columns[0];
        for (let i = 1; i < columns.length; i += 1) {
          if (columns[i].offsetHeight < target.offsetHeight) {
            target = columns[i];
          }
        }
        target.appendChild(card);
      });
    }

    function loadMoreDiscover() {
      if (loading || !hasNext) return;
      loading = true;

      page += 1;
      const url = new URL(w.location.href);
      url.searchParams.set("page", String(page));
      url.searchParams.set("ajax", "1");

      w
        .fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network error");
          return response.json();
        })
        .then((data) => {
          if (data && data.html) appendHtmlToColumns(data.html);
          hasNext = Boolean(data && data.has_next);
          loading = false;
        })
        .catch(() => {
          loading = false;
        });
    }

    const onScroll = () => {
      if (loading || !hasNext) return;
      const scrollPosition = w.innerHeight + w.scrollY;
      const threshold = doc.body.offsetHeight - 300;
      if (scrollPosition >= threshold) {
        loadMoreDiscover();
      }
    };

    w.addEventListener("scroll", onScroll);
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
