{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const mapJsonResponse = (mapResponse, json) => {
  if (typeof mapResponse === "function") return mapResponse(json);
  return {
    html: (json && json.html) || "",
    hasMore: Boolean(json && json.has_more),
    nextPage: json ? json.next_page : null
  };
};

const buildJsonUrl = (w, options, page) => {
  const url = new URL(options.endpoint, w.location.origin);
  url.searchParams.set(options.pageParam, String(page));
  if (options.pageSizeParam && options.pageSize) {
    url.searchParams.set(options.pageSizeParam, String(options.pageSize));
  }
  Object.entries(options.extraParams || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    url.searchParams.set(key, String(value));
  });
  return url;
};

const resolveFetchContext = (win) => {
  const w = win || globalWindow || (typeof window !== "undefined" ? window : null);
  if (!w) return null;
  const origin =
    (w.location && w.location.origin) ||
    (globalWindow && globalWindow.location && globalWindow.location.origin) ||
    "http://localhost";
  return { w, fetchFn: w.fetch || (typeof fetch !== "undefined" ? fetch : null), origin };
};

const buildJsonFetcher = (win, options) => {
  const ctx = resolveFetchContext(win);
  if (!ctx || !options || !options.endpoint) return null;
  const opts = {
    endpoint: options.endpoint,
    pageParam: options.pageParam || "page",
    pageSizeParam: options.pageSizeParam,
    pageSize: options.pageSize,
    extraParams: options.extraParams || {},
    fetchInit: options.fetchInit || {},
    mapResponse: options.mapResponse
  };
  return ({ page }) => {
    if (!page && page !== 0) return Promise.resolve({ html: "", hasMore: false, nextPage: null });
    const url = buildJsonUrl({ location: { origin: ctx.origin } }, opts, page);
    if (!ctx.fetchFn) return Promise.reject(new Error("fetch unavailable"));
    return ctx.fetchFn(url.toString(), opts.fetchInit)
      .then((resp) => {
        if (!resp.ok) throw new Error("Request failed");
        return resp.json();
      })
      .then((json) => mapJsonResponse(opts.mapResponse, json));
  };
};

const createInfiniteState = (win, opts) => {
  const w = resolveWindow(win);
  if (!w || !opts || !opts.sentinel || !opts.fetchPage || !opts.append) return null;
  if (!opts.hasMore || !opts.nextPage) return null;
  if (opts.sentinel && opts.sentinel.offsetHeight === 0) {
    opts.sentinel.style.minHeight = "1px";
    opts.sentinel.style.display = "block";
    if (!opts.sentinel.style.width) opts.sentinel.style.width = "100%";
  }
  return {
    w,
    opts,
    sentinel: opts.sentinel,
    hasMore: Boolean(opts.hasMore),
    nextPage: opts.nextPage,
    loading: false,
    observer: null,
    scrollHandler: null,
    fallbackMode: opts.fallbackMode || "sentinel"
  };
};

const applyPayload = (state, payload) => {
  const html = payload && payload.html ? payload.html : "";
  state.opts.append(html, { page: state.nextPage });
  state.hasMore = Boolean(payload && payload.hasMore);
  state.nextPage = payload ? payload.nextPage : null;
  if (!state.hasMore && state.observer && typeof state.observer.disconnect === "function") {
    state.observer.disconnect();
  }
};

const fetchMore = (state) => {
  if (state.loading || !state.hasMore || !state.nextPage) return;
  state.loading = true;
  state.opts
    .fetchPage({ page: state.nextPage })
    .then((payload) => applyPayload(state, payload))
    .catch(() => {})
    .finally(() => {
      state.loading = false;
    });
};

const setupObserver = (state) => {
  if (!("IntersectionObserver" in state.w)) return null;
  const observerOptions = state.opts.observerOptions || { root: state.opts.root || null, threshold: 0 };
  const observer = new state.w.IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) fetchMore(state);
    });
  }, observerOptions);
  observer.observe(state.sentinel);
  return observer;
};

const shouldTriggerDocumentScroll = (state, margin) => {
  if (!state.w.document || !state.w.document.body) return false;
  const threshold = (state.w.document.body.offsetHeight || 0) - margin;
  const scrollPosition = (state.w.innerHeight || 0) + (state.w.scrollY || 0);
  return scrollPosition >= threshold;
};

const getTriggerMargin = (state) => {
  const margin = Number.isFinite(state.opts.fallbackMargin) ? state.opts.fallbackMargin : 300;
  const viewportMargin = Math.floor((state.w.innerHeight || 0) * 0.6);
  return Math.max(margin, viewportMargin);
};

const minColumnBottom = (state) => {
  const cols = state.opts.columns;
  const w = state.w;
  if (!cols || !cols.length || !w || !w.document) return null;
  let min = null;
  cols.forEach((col) => {
    if (!col || typeof col.getBoundingClientRect !== "function") return;
    const rect = col.getBoundingClientRect();
    const bottom = rect.bottom + (w.scrollY || 0);
    if (min === null || bottom < min) min = bottom;
  });
  return min;
};

const shouldFetchFallback = (state, margin) => {
  const minBottom = minColumnBottom(state);
  const scrollPos = (state.w.scrollY || 0) + (state.w.innerHeight || 0);
  if (minBottom !== null && scrollPos + margin >= minBottom) return true;
  if (state.fallbackMode === "document") return shouldTriggerDocumentScroll(state, margin);
  const rect = state.sentinel.getBoundingClientRect();
  return rect.top - (state.w.innerHeight || 0) <= margin;
};

const setupFallbackScroll = (state) => {
  if (!state.opts.fallbackScroll) return null;
  const handler = () => {
    if (state.loading || !state.hasMore || !state.nextPage) return;
    const triggerMargin = getTriggerMargin(state);
    if (shouldFetchFallback(state, triggerMargin)) fetchMore(state);
  };
  state.w.addEventListener("scroll", handler);
  return handler;
};

const createInfiniteList = (win, opts) => {
  const state = createInfiniteState(win, opts);
  if (!state) return null;
  state.observer = setupObserver(state);
  state.scrollHandler = setupFallbackScroll(state);
  return {
    disconnect() {
      if (state.observer) state.observer.disconnect();
      if (state.scrollHandler) state.w.removeEventListener("scroll", state.scrollHandler);
    },
    trigger() {
      fetchMore(state);
    }
  };
};

const placeInColumns = (nodes, columns) => {
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
};

const attachGlobal = (win) => {
  const w = win || globalWindow;
  if (!w) return;
  w.InfiniteList = {
    create: (opts) => createInfiniteList(w, opts),
    buildJsonFetcher: (opts) => buildJsonFetcher(w, opts),
    placeInColumns
  };
};

if (hasModuleExports) {
  module.exports = { createInfiniteList, buildJsonFetcher, attachGlobal, placeInColumns };
}

/* istanbul ignore next */
if (globalWindow && globalWindow.document) {
  attachGlobal(globalWindow);
}
}
