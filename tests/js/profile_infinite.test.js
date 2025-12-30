const modulePath = "../../static/js/profile_infinite";

function loadModule() {
  jest.resetModules();
  delete global.ProfileInfinite;
  return require(modulePath);
}

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("profile_infinite", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    window.scrollTo = jest.fn();
    delete window.InfiniteList;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    delete window.InfiniteList;
    jest.clearAllMocks();
  });

  test("skips profile posts init when columns are missing", () => {
    const { initProfileInfinite } = loadModule();
    window.history.scrollRestoration = "auto";
    window.InfiniteList = { create: jest.fn() };

    document.body.innerHTML = `
      <div id="profile-posts-grid"></div>
      <div id="profile-posts-sentinel" data-endpoint="/profile/posts" data-has-more="true" data-next-page="3"></div>
    `;

    initProfileInfinite(window, document);

    expect(window.InfiniteList.create).not.toHaveBeenCalled();
    expect(window.history.scrollRestoration).toBe("auto");
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  test("sets scroll restoration, parses next page, and guards append", async () => {
    const { initProfileInfinite } = loadModule();
    window.history.scrollRestoration = "auto";
    window.InfiniteList = { create: jest.fn() };
    global.fetch = jest.fn(() => Promise.resolve({ text: () => Promise.resolve("<div class='my-recipe-card'></div>") }));

    document.body.innerHTML = `
      <div id="profile-posts-grid">
        <div id="profile-posts-col-1"></div>
        <div id="profile-posts-col-2"></div>
        <div id="profile-posts-col-3"></div>
      </div>
      <div id="profile-posts-sentinel" data-endpoint="/profile/posts" data-has-more="true" data-next-page="not-a-number"></div>
    `;

    initProfileInfinite(window, document);

    expect(window.history.scrollRestoration).toBe("manual");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(window.InfiniteList.create).toHaveBeenCalledTimes(1);

    const options = window.InfiniteList.create.mock.calls[0][0];
    expect(options.nextPage).toBeNull();
    expect(options.append("")).toBe(0);
    const result = await options.fetchPage({ page: 5 });
    expect(global.fetch).toHaveBeenCalledWith("/profile/posts?page=5&posts_only=1", { headers: { "HX-Request": "true" } });
    expect(result).toEqual({ html: "<div class='my-recipe-card'></div>", hasMore: false, nextPage: null });
  });

  test("creates follow list infinite loader when modal is shown", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    const applyCloseFriendsFilter = jest.fn();
    const modalSuccessHandlers = { followersModal: jest.fn() };
    const createSpy = jest.fn();
    window.InfiniteList = { create: createSpy };
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            html: `<li data-id="a"></li><li data-id="b"></li>`,
            has_more: true,
            next_page: 3,
            total: 3,
          }),
      })
    );

    document.body.innerHTML = `
      <div id="followersModal" class="modal">
        <div class="modal-body" data-list-type="followers" data-endpoint="/followers" data-has-more="true" data-next-page="2">
          <ul class="follow-list-items"><li id="existing"></li></ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
    `;

    initProfileInfinite(window, document, { attachAjaxModalForms, applyCloseFriendsFilter, modalSuccessHandlers });
    document.getElementById("followersModal").dispatchEvent(new Event("shown.bs.modal"));

    expect(createSpy).toHaveBeenCalledTimes(1);
    const options = createSpy.mock.calls[0][0];
    const payload = await options.fetchPage({ page: 2 });
    expect(global.fetch).toHaveBeenCalledWith("http://localhost/followers?page=2", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    options.append(payload.html);
    const items = document.querySelectorAll("#followersModal .follow-list-items li");
    expect(items).toHaveLength(3);
    expect(items[1].dataset.id).toBe("a");
    expect(items[2].dataset.id).toBe("b");
    expect(attachAjaxModalForms).toHaveBeenCalledWith("followersModal", modalSuccessHandlers.followersModal);
    expect(applyCloseFriendsFilter).not.toHaveBeenCalled();
  });

  test("follow fetcher handles failures gracefully", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    const createSpy = jest.fn();
    window.InfiniteList = { create: createSpy };
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));

    document.body.innerHTML = `
      <div id="followingModal" class="modal">
        <div class="modal-body" data-list-type="following" data-endpoint="/following" data-has-more="true" data-next-page="5">
          <ul class="follow-list-items"><li id="keep"></li></ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
    `;

    initProfileInfinite(window, document, { attachAjaxModalForms });
    document.getElementById("followingModal").dispatchEvent(new Event("shown.bs.modal"));

    expect(createSpy).toHaveBeenCalledTimes(1);
    const options = createSpy.mock.calls[0][0];
    const payload = await options.fetchPage({ page: 5 });

    expect(payload).toEqual({ html: "", hasMore: false, nextPage: null, total: null });
    expect(attachAjaxModalForms).not.toHaveBeenCalled();
  });

  test("ignores follow loaders when endpoint is missing", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    global.fetch = jest.fn();

    document.body.innerHTML = `
      <div id="closeFriendsModal" class="modal">
        <div class="modal-body" data-list-type="close_friends" data-endpoint="" data-has-more="false" data-next-page="">
          <ul class="follow-list-items"><li id="keep"></li></ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
    `;

    initProfileInfinite(window, document, { attachAjaxModalForms });
    document.getElementById("closeFriendsModal").dispatchEvent(new Event("shown.bs.modal"));
    await flushPromises();

    expect(global.fetch).not.toHaveBeenCalled();
    expect(document.querySelectorAll("#closeFriendsModal .follow-list-items li")).toHaveLength(1);
    expect(attachAjaxModalForms).not.toHaveBeenCalled();
  });
});
