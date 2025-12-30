const globalWindow = typeof window !== "undefined" ? window : null;

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

function parseHasMore(value) {
  return String(value || "").toLowerCase() === "true";
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
  if (!endpoint || !infinite.create) return;
  const hasMore = sentinel.getAttribute("data-has-more") === "true";
  const nextPage = parseNextPage(sentinel.getAttribute("data-next-page"));
  const placeCards = createColumnPlacer(columns);
  infinite.create({
    sentinel,
    hasMore,
    nextPage,
    fetchPage: createProfileFetcher(w, endpoint),
    append: createProfileAppendHtml(placeCards),
    columns,
    observerOptions: { root: null, threshold: 0, rootMargin: "1200px 0px" },
    fallbackScroll: true, fallbackMargin: 600, fallbackMode: "document",
  });
}

function createFollowListAppend(doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter, listEl) {
  return (html) => {
    if (!html) return 0;
    const tmp = doc.createElement("div");
    tmp.innerHTML = html;
    let count = 0;
    tmp.querySelectorAll("li").forEach((li) => {
      listEl.appendChild(li);
      count += 1;
    });
    attachAjaxModalForms(modalId, modalSuccessHandlers[modalId]);
    if (listType === "close_friends") {
      applyCloseFriendsFilter();
    }
    return count;
  };
}

function getFollowListElements(doc, modalId) {
  const modalEl = doc.getElementById(modalId);
  if (!modalEl) return null;
  const modalBody = modalEl.querySelector(".modal-body[data-list-type]");
  const listEl = modalEl.querySelector(".follow-list-items");
  const sentinel = modalEl.querySelector(".follow-list-sentinel");
  return modalBody && listEl && sentinel ? { modalEl, modalBody, listEl, sentinel } : null;
}

function getFollowOrigin(w) {
  return (
    (w && w.location && w.location.origin) ||
    (globalWindow && globalWindow.location && globalWindow.location.origin) ||
    "http://localhost"
  );
}

function buildFollowListFetcher(w, endpoint) {
  if (!endpoint) return null;
  const origin = getFollowOrigin(w);
  const mapPayload = (payload) => ({
    html: (payload && payload.html) || "",
    hasMore: Boolean(payload && payload.has_more),
    nextPage: payload ? payload.next_page : null,
    total: payload && payload.total,
  });
  const failPayload = { html: "", hasMore: false, nextPage: null, total: null };

  return ({ page, pageSize }) => {
    if (!page && page !== 0) return Promise.resolve(failPayload);
    const url = new URL(endpoint, origin);
    url.searchParams.set("page", String(page));
    if (pageSize) url.searchParams.set("page_size", String(pageSize));
    const init = { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" };
    return w
      .fetch(url.toString(), init)
      .then((resp) => (resp && resp.ok ? resp.json() : Promise.reject()))
      .then(mapPayload)
      .catch(() => failPayload);
  };
}

function createFollowInfinite(infinite, modalBody, config) {
  if (modalBody.dataset.followInfinite === "1") return;
  if (!infinite.create || !config.hasMore || !config.nextPage) return;
  modalBody.dataset.followInfinite = "1";
  infinite.create({
    sentinel: config.sentinel,
    hasMore: config.hasMore,
    nextPage: config.nextPage,
    fetchPage: config.fetchPage,
    append: config.append,
    observerOptions: { root: modalBody, threshold: 0, rootMargin: "400px 0px" },
  });
}

function buildFollowConfig(modalBody, sentinel, fetchPage, append) {
  return {
    sentinel,
    fetchPage,
    append,
    hasMore: parseHasMore(modalBody.getAttribute("data-has-more")),
    nextPage: parseNextPage(modalBody.getAttribute("data-next-page")),
  };
}

function initFollowListLoader(w, doc, modalId, listType, attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter) {
  const nodes = getFollowListElements(doc, modalId);
  if (!nodes) return;
  const { modalEl, modalBody, listEl, sentinel } = nodes;
  const fetchPage = buildFollowListFetcher(w, modalBody.getAttribute("data-endpoint"));
  if (!fetchPage || !sentinel) return;
  const append = createFollowListAppend(
    doc,
    modalId,
    listType,
    attachAjaxModalForms,
    modalSuccessHandlers,
    applyCloseFriendsFilter,
    listEl,
  );
  if (listType === "close_friends") applyCloseFriendsFilter();

  const infinite = w.InfiniteList || {};
  const startInfinite = () => createFollowInfinite(infinite, modalBody, buildFollowConfig(modalBody, sentinel, fetchPage, append));

  if (modalEl) {
    modalEl.addEventListener("shown.bs.modal", startInfinite);
  }
  startInfinite();
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
} else if (globalWindow) {
  globalWindow.ProfileInfinite = api;
}
