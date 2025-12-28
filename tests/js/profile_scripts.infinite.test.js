const path = "../../static/js/profile_scripts";

function loadModule() {
  jest.resetModules();
  delete global.__profileScriptsInitialized;
  const mod = require(path);
  delete global.__profileScriptsInitialized;
  return mod;
}

describe("profile_scripts infinite lists", () => {
  let originalFetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    delete global.bootstrap;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    delete global.bootstrap;
    delete global.InfiniteList;
    delete window.scrollTo;
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test("profile posts infinite falls back to manual placement when placeInColumns is missing", async () => {
    window.history.scrollRestoration = "auto";
    window.scrollTo = jest.fn();
    const createSpy = jest.fn();
    window.InfiniteList = { create: createSpy };
    const { initProfileScripts } = loadModule();
    document.body.innerHTML = `
      <div id="profile-posts-grid">
        <div id="profile-posts-col-1"></div>
        <div id="profile-posts-col-2"></div>
        <div id="profile-posts-col-3"></div>
      </div>
      <div id="profile-posts-sentinel" data-endpoint="/profile/posts" data-has-more="true" data-next-page="2"></div>
    `;
    initProfileScripts(window);

    expect(createSpy).toHaveBeenCalledTimes(1);
    const options = createSpy.mock.calls[0][0];
    const columns = [
      document.getElementById("profile-posts-col-1"),
      document.getElementById("profile-posts-col-2"),
      document.getElementById("profile-posts-col-3"),
    ];

    expect(options.append("<div></div>")).toBe(0);
    const appendedCount = options.append(`
      <div class="my-recipe-card" id="card-1"></div>
      <div class="my-recipe-card" id="card-2"></div>
    `);
    expect(appendedCount).toBe(2);
    expect(columns[0].querySelector("#card-1")).not.toBeNull();
    expect(columns[1].querySelector("#card-2")).not.toBeNull();
  });

  test("profile posts infinite uses provided column placer and profile fetcher branches", async () => {
    window.history.scrollRestoration = "auto";
    window.scrollTo = jest.fn();
    const createSpy = jest.fn();
    window.InfiniteList = { placeInColumns: jest.fn(), create: createSpy };
    const { initProfileScripts } = loadModule();
    document.body.innerHTML = `
      <div id="profile-posts-grid">
        <div id="profile-posts-col-1"></div>
        <div id="profile-posts-col-2"></div>
        <div id="profile-posts-col-3"></div>
      </div>
      <div id="profile-posts-sentinel" data-endpoint="/profile/posts?tab=favs" data-has-more="false" data-next-page=""></div>
    `;
    global.fetch = jest.fn();

    initProfileScripts(window);

    expect(createSpy).toHaveBeenCalledTimes(1);
    const options = createSpy.mock.calls[0][0];
    options.append(`<div class="my-recipe-card" id="append-card"></div>`);
    const cols = [
      document.getElementById("profile-posts-col-1"),
      document.getElementById("profile-posts-col-2"),
      document.getElementById("profile-posts-col-3"),
    ];
    expect(cols[0].querySelector("#append-card")).not.toBeNull();

    global.fetch.mockResolvedValueOnce({ text: () => Promise.resolve("   ") });
    const emptyResult = await options.fetchPage({ page: 2 });
    expect(emptyResult).toEqual({ html: "", hasMore: false, nextPage: null });

    global.fetch.mockResolvedValueOnce({ text: () => Promise.resolve("<div class='my-recipe-card'></div>") });
    const singleResult = await options.fetchPage({ page: 3 });
    expect(singleResult).toEqual({ html: "<div class='my-recipe-card'></div>", hasMore: false, nextPage: null });

    const dozen = Array.from({ length: 12 }, (_, i) => `<div class="my-recipe-card" id="c${i}"></div>`).join("");
    global.fetch.mockResolvedValueOnce({ text: () => Promise.resolve(dozen) });
    const manyResult = await options.fetchPage({ page: 4 });
    expect(manyResult).toEqual({ html: dozen, hasMore: true, nextPage: 5 });

    global.fetch.mockRejectedValueOnce(new Error("fail"));
    const failureResult = await options.fetchPage({ page: 5 });
    expect(failureResult).toEqual({ html: "", hasMore: false, nextPage: null });
  });

  test("follow list loader appends close friends items and reapplies filter", async () => {
    window.scrollTo = jest.fn();
    const createLoader = jest.fn((opts) => {
      return opts.fetchPage({ page: 1 }).then(({ html }) => {
        opts.append(html);
        opts.append("");
      });
    });
    const buildJsonFetcher = jest.fn(({ mapResponse }) => async () =>
      mapResponse({
        html: `<li class="close-friend-item" data-name="alice"><form action="/friends/add/1/"></form></li>`,
        has_more: false,
        next_page: null,
      })
    );
    window.InfiniteList = { create: createLoader, buildJsonFetcher };

    const { initProfileScripts } = loadModule();
    document.body.innerHTML = `
      <input id="closeFriendsSearch" value="bob" />
      <div id="closeFriendsModal">
        <div class="modal-body" data-list-type="close_friends" data-endpoint="/friends" data-has-more="true" data-next-page="3">
          <ul id="closeFriendsList" class="follow-list-items">
            <li class="close-friend-item" data-name="bob"></li>
          </ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
      <div id="profile-posts-grid"></div>
    `;
    initProfileScripts(window);

    await createLoader.mock.results[0].value;
    expect(buildJsonFetcher).toHaveBeenCalled();
    expect(createLoader).toHaveBeenCalled();
    const closeFriendsItems = document.querySelectorAll("#closeFriendsList .close-friend-item");
    expect(closeFriendsItems.length).toBe(2);
    expect(closeFriendsItems[1].style.display).toBe("none");
  });
});
