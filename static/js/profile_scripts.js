(function (global) {
  const FOLLOW_MODAL_CONFIGS = [
    ['[data-bs-target="#followersModal"]', "followersModal"],
    ['[data-bs-target="#followingModal"]', "followingModal"],
    ['[data-bs-target="#closeFriendsModal"]', "closeFriendsModal"],
    ['[data-bs-target="#editProfileModal"]', "editProfileModal"],
  ];
  function resolveWindow(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    return w && w.document ? w : null;
  }
  function markInitialized(w, flag) {
    if (w[flag]) return false;
    w[flag] = true;
    return true;
  }
  function buildBackdrop(doc) {
    const el = doc.createElement("div");
    el.className = "modal-backdrop fade custom-modal-backdrop";
    doc.body.appendChild(el);
    return el;
  }
  function createFallbackModalController(w, doc) {
    let backdrop = null;
    let current = null;
    const lockBody = (locked) => {
      doc.body.classList.toggle("modal-open", locked);
      doc.body.style.overflow = locked ? "hidden" : "";
    };
    const hide = () => {
      if (!current) return;
      current.classList.remove("show");
      current.style.display = "none";
      current.setAttribute("aria-hidden", "true");
      if (backdrop) {
        backdrop.classList.remove("show");
        backdrop.style.display = "none";
        backdrop.onclick = null;
      }
      lockBody(false);
      current = null;
    };
    const show = (modalEl) => {
      current = modalEl;
      backdrop = backdrop || buildBackdrop(doc);
      backdrop.style.display = "block";
      w.setTimeout(() => backdrop.classList.add("show"), 0);
      modalEl.classList.add("show");
      modalEl.style.display = "block";
      modalEl.removeAttribute("aria-hidden");
      lockBody(true);
      backdrop.onclick = hide;
    };
    return { show, hide };
  }

  function wireFollowModal(w, doc, modalCtrl, usingBootstrap, selector, modalId) {
    const buttons = doc.querySelectorAll(selector);
    const modalEl = doc.getElementById(modalId);
    if (!buttons.length || !modalEl) return;
    if (!usingBootstrap) {
      modalEl.addEventListener("click", (event) => {
        if (event.target === modalEl) modalCtrl.hide();
      });
      const closeBtn = modalEl.querySelector("[data-bs-dismiss='modal'], .btn-close");
      if (closeBtn) {
        closeBtn.addEventListener("click", (event) => {
          event.preventDefault();
          modalCtrl.hide();
        });
      }
    }
    const open = () => {
      if (usingBootstrap) {
        w.bootstrap.Modal.getOrCreateInstance(modalEl).show();
      } else {
        modalCtrl.show(modalEl);
      }
    };
    buttons.forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        open();
      });
    });
  }

  function wireFollowModals(w, doc, modalCtrl) {
    const usingBootstrap = !!(w.bootstrap && w.bootstrap.Modal);
    FOLLOW_MODAL_CONFIGS.forEach(([selector, modalId]) => {
      wireFollowModal(w, doc, modalCtrl, usingBootstrap, selector, modalId);
    });
  }

  function handleFollowToggleSubmit(w, form, event) {
    event.preventDefault();
    const url = form.getAttribute("action");
    if (!url) return;
    const formData = new w.FormData(form);
    w
      .fetch(url, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      })
      .then((response) => {
        if (!response.ok) {
          form.submit();
          return;
        }
        const li = form.closest("li");
        if (li) li.remove();
      })
      .catch(() => form.submit());
  }

  function bindFollowToggleForm(w, form) {
    const btn = form.querySelector(".follow-toggle-btn");
    if (!btn) return;
    const followingLabel = btn.getAttribute("data-label-following") || "Following";
    const unfollowLabel = btn.getAttribute("data-label-unfollow") || "Unfollow";
    btn.addEventListener("mouseenter", () => {
      btn.textContent = unfollowLabel;
    });
    btn.addEventListener("mouseleave", () => {
      btn.textContent = followingLabel;
    });
    form.addEventListener("submit", (event) => handleFollowToggleSubmit(w, form, event));
  }

  function bindFollowToggles(w, doc) {
    doc.querySelectorAll(".follow-toggle-form").forEach((form) => {
      bindFollowToggleForm(w, form);
    });
  }

  function setupCloseFriendsFilter(doc) {
    const searchInput = doc.getElementById("closeFriendsSearch");
    const list = doc.getElementById("closeFriendsList");
    if (!searchInput || !list) return () => {};
    const apply = () => {
      const term = (searchInput.value || "").trim().toLowerCase();
      list.querySelectorAll(".close-friend-item").forEach((item) => {
        const name = item.getAttribute("data-name") || "";
        const match = !term || name.indexOf(term) !== -1;
        item.style.display = match ? "" : "none";
      });
    };
    searchInput.addEventListener("input", apply);
    return apply;
  }

  function createAjaxModalBinder(w, doc) {
    return (modalId, onSuccess) => {
      const modalEl = doc.getElementById(modalId);
      if (!modalEl) return;
      modalEl.querySelectorAll("form").forEach((form) => {
        if (form.dataset.ajaxBound === "1") return;
        form.dataset.ajaxBound = "1";
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          const url = form.getAttribute("action");
          if (!url) return;
          const formData = new w.FormData(form);
          w
            .fetch(url, {
              method: "POST",
              body: formData,
              headers: { "X-Requested-With": "XMLHttpRequest" },
              credentials: "same-origin",
            })
            .then((response) => {
              if (!response.ok) throw new Error("Request failed");
              return response.json().catch(() => ({}));
            })
            .then((payload) => {
              if (typeof onSuccess === "function") onSuccess({ form, url, payload: payload || {} });
            })
            .catch(() => form.submit());
        });
      });
    };
  }

  function createModalSuccessHandlers(applyCloseFriendsFilter) {
    return {
      closeFriendsModal: (ctx) => {
        const form = ctx.form;
        const url = ctx.url;
        const btn = form.querySelector("button");
        const isAdd = url.indexOf("/add/") !== -1;
        const toggled = isAdd ? url.replace("/add/", "/remove/") : url.replace("/remove/", "/add/");
        form.setAttribute("action", toggled);
        if (btn) {
          btn.textContent = isAdd ? "Remove" : "Add";
        }
        applyCloseFriendsFilter();
      },
      followersModal: (ctx) => {
        const li = ctx.form.closest("li");
        if (li) li.remove();
      },
      followingModal: (ctx) => {
        const li = ctx.form.closest("li");
        if (li) li.remove();
      },
    };
  }

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
  function initProfileScripts(win) {
    const w = resolveWindow(win);
    if (!w) return;
    if (!markInitialized(w, "__profileScriptsInitialized")) return;
    const doc = w.document;
    const modalCtrl = createFallbackModalController(w, doc);
    const applyCloseFriendsFilter = setupCloseFriendsFilter(doc);
    const attachAjaxModalForms = createAjaxModalBinder(w, doc);
    const modalSuccessHandlers = createModalSuccessHandlers(applyCloseFriendsFilter);
    wireFollowModals(w, doc, modalCtrl);
    bindFollowToggles(w, doc);
    attachAjaxModalForms("closeFriendsModal", modalSuccessHandlers.closeFriendsModal);
    attachAjaxModalForms("followersModal", modalSuccessHandlers.followersModal);
    attachAjaxModalForms("followingModal", modalSuccessHandlers.followingModal);
    initFollowListLoader(w, doc, "followersModal", "followers", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
    initFollowListLoader(w, doc, "followingModal", "following", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
    initFollowListLoader(w, doc, "closeFriendsModal", "close_friends", attachAjaxModalForms, modalSuccessHandlers, applyCloseFriendsFilter);
    initProfilePostsInfinite(w, doc);
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initProfileScripts };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initProfileScripts(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);