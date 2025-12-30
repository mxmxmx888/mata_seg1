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

  test("loads follow list immediately when no modal wrapper is present", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    const applyCloseFriendsFilter = jest.fn();
    window.InfiniteList = {};
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            html: `<li data-id="a"></li><li data-id="b"></li>`,
            has_more: true,
            next_page: 2,
            total: 2,
          }),
      })
    );

    document.body.innerHTML = `
      <div id="followersModal">
        <div class="modal-body" data-list-type="followers" data-endpoint="/followers">
          <ul class="follow-list-items"><li id="existing"></li></ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
    `;

    initProfileInfinite(window, document, { attachAjaxModalForms, applyCloseFriendsFilter });
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith("http://localhost/followers?page=1&page_size=100000", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    const items = document.querySelectorAll("#followersModal .follow-list-items li");
    expect(items).toHaveLength(2);
    expect(items[0].dataset.id).toBe("a");
    expect(items[1].dataset.id).toBe("b");
    expect(attachAjaxModalForms).toHaveBeenCalledWith("followersModal", undefined);
    expect(applyCloseFriendsFilter).not.toHaveBeenCalled();
  });

  test("modal path listens for shown event and handles fetch failures", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    window.InfiniteList = {};
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));

    document.body.innerHTML = `
      <div id="followingModal" class="modal">
        <div class="modal-body" data-list-type="following" data-endpoint="/following">
          <ul class="follow-list-items"><li id="keep"></li></ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
    `;

    initProfileInfinite(window, document, { attachAjaxModalForms });
    document.getElementById("followingModal").dispatchEvent(new Event("shown.bs.modal"));
    await flushPromises();

    expect(global.fetch).toHaveBeenCalled();
    expect(document.querySelectorAll("#followingModal .follow-list-items li")).toHaveLength(0);
    expect(attachAjaxModalForms).not.toHaveBeenCalled();
  });

  test("ignores follow loaders when endpoint is missing", async () => {
    const { initProfileInfinite } = loadModule();
    const attachAjaxModalForms = jest.fn();
    global.fetch = jest.fn();

    document.body.innerHTML = `
      <div id="closeFriendsModal" class="modal">
        <div class="modal-body" data-list-type="close_friends" data-endpoint="">
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
