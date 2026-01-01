const path = "../../static/js/profile_scripts";

function loadModule() {
  jest.resetModules();
  delete global.__profileScriptsInitialized;
  const mod = require(path);
  delete global.__profileScriptsInitialized;
  return mod;
}

const gridMarkup = (endpoint, nextPage, hasMore = "true") => `
      <div id="profile-posts-grid">
        <div id="profile-posts-col-1"></div>
        <div id="profile-posts-col-2"></div>
        <div id="profile-posts-col-3"></div>
      </div>
      <div id="profile-posts-sentinel" data-endpoint="${endpoint}" data-has-more="${hasMore}" data-next-page="${nextPage}"></div>
    `;

const getColumns = () => [
  document.getElementById("profile-posts-col-1"),
  document.getElementById("profile-posts-col-2"),
  document.getElementById("profile-posts-col-3"),
];

function setupProfilePosts({ endpoint = "/profile/posts", nextPage = "2", hasMore = "true", placeInColumns } = {}) {
  window.history.scrollRestoration = "auto";
  window.scrollTo = jest.fn();
  const createSpy = jest.fn();
  window.InfiniteList = { create: createSpy, ...(placeInColumns ? { placeInColumns } : {}) };
  const { initProfileScripts } = loadModule();
  document.body.innerHTML = gridMarkup(endpoint, nextPage, hasMore);
  initProfileScripts(window);
  return { options: createSpy.mock.calls[0][0], createSpy };
}

function setupCloseFriends({ response }) {
  window.scrollTo = jest.fn();
  const createSpy = jest.fn();
  window.InfiniteList = { create: createSpy };
  const { initProfileScripts } = loadModule();
  document.body.innerHTML = `
      <input id="closeFriendsSearch" value="bob" />
      <div id="closeFriendsModal" class="modal">
        <div class="modal-body" data-list-type="close_friends" data-endpoint="/friends" data-has-more="true" data-next-page="3">
          <ul id="closeFriendsList" class="follow-list-items">
            <li class="close-friend-item" data-name="bob"></li>
          </ul>
          <div class="follow-list-sentinel"></div>
        </div>
      </div>
      <div id="profile-posts-grid"></div>
    `;
  global.fetch = jest.fn(() => Promise.resolve(response));
  initProfileScripts(window);
  document.getElementById("closeFriendsModal").dispatchEvent(new Event("shown.bs.modal"));
  return { options: createSpy.mock.calls[0][0] };
}

let originalFetch;

describe("profile_scripts infinite lists", () => {
  beforeEach(setupProfileInfiniteListsEnv);
  afterEach(teardownProfileInfiniteListsEnv);
  testProfilePostsFallbackPlacement();
  testProfilePostsUsesProvidedColumnPlacer();
  testFollowListLoaderAppendsCloseFriends();
});

function setupProfileInfiniteListsEnv() {
  document.body.innerHTML = "";
  originalFetch = global.fetch;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
  delete global.bootstrap;
}

function teardownProfileInfiniteListsEnv() {
  global.fetch = originalFetch;
  delete global.bootstrap;
  delete global.InfiniteList;
  delete window.scrollTo;
  jest.useRealTimers();
  jest.clearAllMocks();
}

function testProfilePostsFallbackPlacement() {
  test("profile posts infinite falls back to manual placement when placeInColumns is missing", async () => {
    const { options } = setupProfilePosts();
    const columns = getColumns();
    expect(options.append("<div></div>")).toBe(0);
    const appendedCount = options.append(`
      <div class="my-recipe-card" id="card-1"></div>
      <div class="my-recipe-card" id="card-2"></div>
    `);
    expect(appendedCount).toBe(2);
    expect(columns[0].querySelector("#card-1")).not.toBeNull();
    expect(columns[1].querySelector("#card-2")).not.toBeNull();
  });
}

function testProfilePostsUsesProvidedColumnPlacer() {
  test("profile posts infinite uses provided column placer and profile fetcher branches", async () => {
    const placeInColumns = jest.fn();
    global.fetch = jest.fn();
    const { options } = setupProfilePosts({
      endpoint: "/profile/posts?tab=favs",
      hasMore: "false",
      nextPage: "",
      placeInColumns,
    });
    expect(options.append(`<div class="my-recipe-card" id="append-card"></div>`)).toBe(1);
    global.fetch.mockResolvedValueOnce({ text: () => Promise.resolve("   ") });
    expect(await options.fetchPage({ page: 2 })).toEqual({ html: "", hasMore: false, nextPage: null });
    const dozen = Array.from({ length: 12 }, (_, i) => `<div class="my-recipe-card" id="c${i}"></div>`).join("");
    global.fetch.mockResolvedValueOnce({ text: () => Promise.resolve(dozen) });
    expect(await options.fetchPage({ page: 4 })).toEqual({ html: dozen, hasMore: true, nextPage: 5 });
    global.fetch.mockRejectedValueOnce(new Error("fail"));
    expect(await options.fetchPage({ page: 5 })).toEqual({ html: "", hasMore: false, nextPage: null });
  });
}

function testFollowListLoaderAppendsCloseFriends() {
  test("follow list loader appends close friends items and reapplies filter", async () => {
    const response = {
      ok: true,
      json: () =>
        Promise.resolve({
          html: `<li class="close-friend-item" data-name="alice"><form action="/friends/add/1/"></form></li>`,
          has_more: false,
          next_page: null,
          total: 2,
        }),
    };
    const { options } = setupCloseFriends({ response });
    const payload = await options.fetchPage({ page: 3 });
    expect(global.fetch).toHaveBeenCalledWith("http://localhost/friends?page=3", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    options.append(payload.html);
    const closeFriendsItems = document.querySelectorAll("#closeFriendsList .close-friend-item");
    expect(closeFriendsItems.length).toBe(2);
    expect(closeFriendsItems[1].dataset.name).toBe("alice");
    expect(closeFriendsItems[1].style.display).toBe("none");
  });
}
