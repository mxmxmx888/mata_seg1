(function (global) {
  function getProfileColumns(doc) {
    return [
      doc.getElementById("profile-posts-col-1"),
      doc.getElementById("profile-posts-col-2"),
      doc.getElementById("profile-posts-col-3"),
    ].filter(Boolean);
  }

  function createColumnPlacer(columns) {
    return (cards) => {
      if (!cards || !cards.length) return;
      const existingCount = columns.reduce((sum, col) => sum + col.children.length, 0);
      cards.forEach((card, index) => {
        const targetIndex = (existingCount + index) % columns.length;
        columns[targetIndex].appendChild(card);
      });
    };
  }

  function createProfileAppendHtml(placeCards) {
    return (html) => {
      if (!html) return 0;
      const parser = new DOMParser();
      const docNode = parser.parseFromString(html, "text/html");
      const cards = Array.from(docNode.querySelectorAll(".my-recipe-card"));
      placeCards(cards);
      return cards.length;
    };
  }

  function parseNextPage(value) {
    const parsed = parseInt(value || "", 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  function countCards(html) {
    return (html.match(/class=["']my-recipe-card["']/g) || []).length;
  }

  function createProfileFetcher(w, endpoint) {
    return ({ page }) => {
      const url = endpoint.includes("?")
        ? `${endpoint}&page=${page}&posts_only=1`
        : `${endpoint}?page=${page}&posts_only=1`;
      return w
        .fetch(url, { headers: { "HX-Request": "true" } })
        .then((resp) => resp.text())
        .then((html) => {
          const trimmed = (html || "").trim();
          const count = trimmed ? countCards(trimmed) : 0;
          return {
            html: trimmed,
            hasMore: count >= 12,
            nextPage: count >= 12 ? page + 1 : null,
          };
        })
        .catch(() => ({ html: "", hasMore: false, nextPage: null }));
    };
  }

  function initProfilePostsInfinite(w, doc) {
    const sentinel = doc.getElementById("profile-posts-sentinel");
    const columns = getProfileColumns(doc);
    if (!sentinel || !doc.getElementById("profile-posts-grid") || !columns.length) return;
    if (w.history && "scrollRestoration" in w.history) w.history.scrollRestoration = "manual";
    w.scrollTo(0, 0);
    const endpoint = sentinel.getAttribute("data-endpoint");
    const infinite = w.InfiniteList || {};
    if (!infinite.create || !endpoint) return;
    const hasMore = sentinel.getAttribute("data-has-more") === "true";
    const nextPage = parseNextPage(sentinel.getAttribute("data-next-page"));
    const placeCards = createColumnPlacer(columns);
    infinite.create({
      sentinel,
      hasMore,
      nextPage,
      fetchPage: createProfileFetcher(w, endpoint),
      append: createProfileAppendHtml(placeCards),
      observerOptions: { root: null, threshold: 0.1 },
      fallbackScroll: true,
      fallbackMargin: 300,
    });
  }

  function createFollowListAppend(doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter, listEl) {
    return (html) => {
      if (!html) return;
      const tmp = doc.createElement("div");
      tmp.innerHTML = html;
      tmp.querySelectorAll("li").forEach((li) => listEl.appendChild(li));
      attachAjaxModalForms(modalId, modalSuccessHandlers[modalId]);
      if (listType === "close_friends") {
        applyCloseFriendsFilter();
      }
    };
  }

  function getFollowListElements(doc, modalId) {
    const modalEl = doc.getElementById(modalId);
    if (!modalEl) return null;
    const modalBody = modalEl.querySelector(".modal-body[data-list-type]");
    const listEl = modalEl.querySelector(".follow-list-items");
    const sentinel = modalEl.querySelector(".follow-list-sentinel");
    return modalBody && listEl && sentinel ? { modalBody, listEl, sentinel } : null;
  }

  function buildFollowListFetcher(infinite, endpoint) {
    if (!endpoint || typeof infinite.buildJsonFetcher !== "function") return null;
    return infinite.buildJsonFetcher({
      endpoint,
      pageParam: "page",
      fetchInit: { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" },
      mapResponse: (payload) => ({
        html: (payload && payload.html) || "",
        hasMore: Boolean(payload && payload.has_more),
        nextPage: payload ? payload.next_page : null,
      }),
    });
  }

  function initFollowListLoader(w, doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter) {
    const nodes = getFollowListElements(doc, modalId);
    if (!nodes) return;
    const { modalBody, listEl, sentinel } = nodes;
    const infinite = w.InfiniteList || {};
    const createLoader = typeof infinite.create === "function" ? infinite.create : null;
    const fetchPage = buildFollowListFetcher(infinite, modalBody.getAttribute("data-endpoint"));
    if (!fetchPage || !createLoader) return;
    createLoader({
      root: modalBody,
      sentinel,
      hasMore: modalBody.getAttribute("data-has-more") === "true",
      nextPage: parseNextPage(modalBody.getAttribute("data-next-page")),
      fetchPage,
      append: createFollowListAppend(doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter, listEl),
      observerOptions: { root: modalBody, threshold: 0.1 },
    });
  }

  function initProfileInfinite(w, doc, deps) {
    const { attachAjaxModalForms = () => {}, modalSuccessHandlers = {}, applyCloseFriendsFilter = () => {} } = deps || {};
    initProfilePostsInfinite(w, doc);
    initFollowListLoader(w, doc, "followersModal", "followers", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
    initFollowListLoader(w, doc, "followingModal", "following", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
    initFollowListLoader(w, doc, "closeFriendsModal", "close_friends", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
  }

  const api = {
    initProfileInfinite,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else if (global) {
    global.ProfileInfinite = api;
  }
})(typeof window !== "undefined" ? window : {});
