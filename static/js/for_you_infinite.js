(function (global) {
  function initForYouInfinite(win) {
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
    let loading = false;
    let hasMore = offset >= LIMIT;

    function setLoading(state) {
      loading = state;
      if (!loadingEl) return;
      loadingEl.classList.toggle("d-none", !state);
    }

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

    function loadMoreForYou() {
      if (loading || !hasMore) return;
      setLoading(true);

      const url = new URL(w.location.href);
      url.searchParams.set("for_you_ajax", "1");
      url.searchParams.set("for_you_offset", String(offset));

      w
        .fetch(url.toString(), {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data && data.html) {
            appendHtmlToColumns(data.html);
            offset += data.count || 0;
            hasMore = Boolean(data.has_more);
          } else {
            hasMore = false;
          }
          setLoading(false);
        })
        .catch(() => {
          setLoading(false);
        });
    }

    const observer = "IntersectionObserver" in w
      ? new w.IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              loadMoreForYou();
            }
          });
        }, { rootMargin: "600px 0px" })
      : null;

    if (observer) {
      observer.observe(sentinel);
    } else {
      w.addEventListener("scroll", () => {
        if (loading || !hasMore) return;
        const scrollPosition = w.innerHeight + w.scrollY;
        const threshold = doc.body.offsetHeight - 300;
        if (scrollPosition >= threshold) {
          loadMoreForYou();
        }
      });
    }
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
