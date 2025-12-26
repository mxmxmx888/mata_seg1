(function (global) {
  /**
   * Build a fetcher that returns JSON payloads for infinite lists.
   * Options:
   * - endpoint: base URL (string, relative allowed)
   * - pageParam: query param name for page (default: "page")
   * - pageSizeParam / pageSize: optional size control
   * - extraParams: object of additional query params
   * - fetchInit: fetch init overrides
   * - mapResponse: function(json) -> { html, hasMore, nextPage }
   */
  function buildJsonFetcher(win, options) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !options || !options.endpoint) return null;

    const {
      endpoint,
      pageParam = "page",
      pageSizeParam,
      pageSize,
      extraParams = {},
      fetchInit = {},
      mapResponse,
    } = options;

    return ({ page }) => {
      if (!page && page !== 0) return Promise.resolve({ html: "", hasMore: false, nextPage: null });
      const url = new URL(endpoint, w.location.origin);
      url.searchParams.set(pageParam, String(page));
      if (pageSizeParam && pageSize) {
        url.searchParams.set(pageSizeParam, String(pageSize));
      }
      Object.entries(extraParams || {}).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        url.searchParams.set(key, String(value));
      });

      return w
        .fetch(url.toString(), fetchInit)
        .then((resp) => {
          if (!resp.ok) throw new Error("Request failed");
          return resp.json();
        })
        .then((json) => {
          if (typeof mapResponse === "function") {
            return mapResponse(json);
          }
          return {
            html: (json && json.html) || "",
            hasMore: Boolean(json && json.has_more),
            nextPage: json ? json.next_page : null,
          };
        });
    };
  }

  /**
   * Create an infinite list loader with IntersectionObserver (and optional scroll fallback).
   * Options:
   * - root: scroll container for observer (default: viewport)
   * - sentinel: element to observe (required)
   * - fetchPage: ({page}) => Promise<{html, hasMore, nextPage}> (required)
   * - append: (html, ctx) => void (required)
   * - hasMore: initial boolean
   * - nextPage: initial page number
   * - observerOptions: options passed to IntersectionObserver
   * - fallbackScroll: enable scroll listener when IntersectionObserver is unavailable
   * - fallbackMargin: px distance from viewport bottom to trigger (default: 300)
   * - fallbackMode: "sentinel" (default) uses the sentinel's position; "document" uses page height.
   */
  function createInfiniteList(win, opts) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !opts || !opts.sentinel || !opts.fetchPage || !opts.append) return null;

    const sentinel = opts.sentinel;
    let hasMore = Boolean(opts.hasMore);
    let nextPage = opts.nextPage;
    let loading = false;
    let observer = null;
    let scrollHandler = null;

    if (!hasMore || !nextPage) return null;

    const observerOptions = opts.observerOptions || { root: opts.root || null, threshold: 0.1 };
    const fallbackMode = opts.fallbackMode || "sentinel"; // "sentinel" | "document"

    function fetchMore() {
      if (loading || !hasMore || !nextPage) return;
      loading = true;
      opts
        .fetchPage({ page: nextPage })
        .then((payload) => {
          const html = payload && payload.html ? payload.html : "";
          opts.append(html, { page: nextPage });
          hasMore = Boolean(payload && payload.hasMore);
          nextPage = payload ? payload.nextPage : null;
          if (!hasMore && observer && typeof observer.disconnect === "function") observer.disconnect();
        })
        .catch(() => {
        })
        .finally(() => {
          loading = false;
        });
    }

    if ("IntersectionObserver" in w) {
      observer = new w.IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            fetchMore();
          }
        });
      }, observerOptions);
      observer.observe(sentinel);
    } else if (opts.fallbackScroll) {
      const margin = Number.isFinite(opts.fallbackMargin) ? opts.fallbackMargin : 300;
      scrollHandler = () => {
        if (loading || !hasMore || !nextPage) return;
        if (fallbackMode === "document" && w.document && w.document.body) {
          const threshold = (w.document.body.offsetHeight || 0) - margin;
          const scrollPosition = (w.innerHeight || 0) + (w.scrollY || 0);
          if (scrollPosition >= threshold) fetchMore();
        } else {
          const rect = sentinel.getBoundingClientRect();
          if (rect.top - (w.innerHeight || 0) <= margin) {
            fetchMore();
          }
        }
      };
      w.addEventListener("scroll", scrollHandler);
    }

    return {
      disconnect() {
        if (observer) observer.disconnect();
        if (scrollHandler) w.removeEventListener("scroll", scrollHandler);
      },
      trigger() {
        fetchMore();
      },
    };
  }

  // Utility to append nodes into the shortest column for masonry-like layouts.
  function placeInColumns(nodes, columns) {
    if (!nodes || !columns || !columns.length) return;
    nodes.forEach((node) => {
      let target = columns[0];
      let minHeight = columns[0].offsetHeight;
      for (let i = 1; i < columns.length; i += 1) {
        const h = columns[i].offsetHeight;
        if (h < minHeight) {
          minHeight = h;
          target = columns[i];
        }
      }
      target.appendChild(node);
    });
  }

  function attachGlobal(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w) return;
    w.InfiniteList = {
      create: (opts) => createInfiniteList(w, opts),
      buildJsonFetcher: (opts) => buildJsonFetcher(w, opts),
      placeInColumns,
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createInfiniteList, buildJsonFetcher, attachGlobal, placeInColumns };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    attachGlobal(global);
  }
})(typeof window !== "undefined" ? window : null);
