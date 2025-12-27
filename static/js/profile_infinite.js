(function (global) {
  function getProfileColumns(doc) {
    return [
      doc.getElementById("profile-posts-col-1"),
      doc.getElementById("profile-posts-col-2"),
      doc.getElementById("profile-posts-col-3"),
    ].filter(Boolean);
  }

  function createColumnPlacer(infinite, columns) {
    return (cards) => {
      if (!cards || !cards.length) return;
      if (typeof infinite.placeInColumns === "function") {
        infinite.placeInColumns(cards, columns);
        return;
      }
      cards.forEach((card) => {
        let target = columns[0];
        let minHeight = columns[0].offsetHeight;
        columns.forEach((col) => {
          const h = col.offsetHeight;
          if (h < minHeight) {
            minHeight = h;
            target = col;
          }
        });
        target.appendChild(card);
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
          if (!trimmed) {
            return { html: "", hasMore: false, nextPage: null };
          }
          const parser = new DOMParser();
          const docNode = parser.parseFromString(trimmed, "text/html");
          const cards = docNode.querySelectorAll(".my-recipe-card");
          const count = cards.length;
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
    const grid = doc.getElementById("profile-posts-grid");
    const columns = getProfileColumns(doc);
    if (!sentinel || !grid || !columns.length) return;
    if (w.history && "scrollRestoration" in w.history) {
      w.history.scrollRestoration = "manual";
    }
    w.scrollTo(0, 0);
    const endpoint = sentinel.getAttribute("data-endpoint");
    const infinite = w.InfiniteList || {};
    if (!infinite.create || !endpoint) return;
    const placeCards = createColumnPlacer(infinite, columns);
    const appendHtml = createProfileAppendHtml(placeCards);
    const hasMore = sentinel.getAttribute("data-has-more") === "true";
    const parsedNext = parseInt(sentinel.getAttribute("data-next-page") || "", 10);
    const nextPage = Number.isNaN(parsedNext) ? null : parsedNext;
    infinite.create({
      sentinel,
      hasMore,
      nextPage,
      fetchPage: createProfileFetcher(w, endpoint),
      append: appendHtml,
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

  function initFollowListLoader(w, doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter) {
    const modalEl = doc.getElementById(modalId);
    if (!modalEl) return;
    const modalBody = modalEl.querySelector(".modal-body[data-list-type]");
    const listEl = modalEl.querySelector(".follow-list-items");
    const sentinel = modalEl.querySelector(".follow-list-sentinel");
    if (!modalBody || !listEl || !sentinel) return;
    const endpoint = modalBody.getAttribute("data-endpoint");
    const hasMore = modalBody.getAttribute("data-has-more") === "true";
    const parsedNext = parseInt(modalBody.getAttribute("data-next-page") || "", 10);
    const nextPage = Number.isNaN(parsedNext) ? null : parsedNext;
    const infinite = w.InfiniteList || {};
    const buildFetcher = typeof infinite.buildJsonFetcher === "function" ? infinite.buildJsonFetcher : null;
    const createLoader = typeof infinite.create === "function" ? infinite.create : null;
    if (!endpoint || !buildFetcher || !createLoader) return;
    const fetchPage = buildFetcher({
      endpoint,
      pageParam: "page",
      fetchInit: {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      },
      mapResponse: (payload) => ({
        html: (payload && payload.html) || "",
        hasMore: Boolean(payload && payload.has_more),
        nextPage: payload ? payload.next_page : null,
      }),
    });
    createLoader({
      root: modalBody,
      sentinel,
      hasMore,
      nextPage,
      fetchPage,
      append: createFollowListAppend(
        doc,
        modalId,
        listType,
        attachAjaxModalForms,
        modalSuccessHandlers,
        applyCloseFriendsFilter,
        listEl
      ),
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
