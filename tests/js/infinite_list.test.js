const { createInfiniteList, buildJsonFetcher, placeInColumns, attachGlobal } = require("../../static/js/infinite_list");

let fetchPage;
let append;
let sentinel;
let cleanupObservers;

describe("buildJsonFetcher", () => {
  testReturnsNullWhenOptionsMissing();
  testResolvesEmptyPayloadWhenPageMissing();
  testInvokesFetchWithParams();
  testSupportsCustomMapResponse();
  testRejectsOnNonOkResponse();
  testDefaultsMappingWhenJsonMissingFields();
});

describe("createInfiniteList", () => {
  beforeEach(setupInfiniteListEnv);
  afterEach(teardownInfiniteListEnv);
  testReturnsNullWhenRequiredOptionsMissing();
  testUsesIntersectionObserver();
  testIgnoresNonIntersectingEntries();
  testFallbackScrollSentinelTriggersFetch();
  testFallbackScrollSkipsWhenAboveThreshold();
  testFallbackDocumentModeTriggersFetch();
  testTriggerHandlesRejection();
  testStopsFetchingWhenNoMorePages();
});

function testReturnsNullWhenOptionsMissing() {
  test("returns null when options or endpoint missing", () => {
    expect(buildJsonFetcher(window, null)).toBeNull();
    expect(buildJsonFetcher(window, { page: 1 })).toBeNull();
    expect(buildJsonFetcher(window, { endpoint: "" })).toBeNull();
  });
}

function testResolvesEmptyPayloadWhenPageMissing() {
  test("resolves empty payload when page missing", async () => {
    const fetcher = buildJsonFetcher(window, { endpoint: "/api/posts" });
    const result = await fetcher({ page: null });
    expect(result).toEqual({ html: "", hasMore: false, nextPage: null });
  });
}

function testInvokesFetchWithParams() {
  test("invokes fetch with params and default mapping", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ html: "<p>hi</p>", has_more: true, next_page: 3 })
      })
    );
    const fetcher = buildJsonFetcher(window, {
      endpoint: "/api/posts",
      pageParam: "p",
      pageSizeParam: "size",
      pageSize: 20,
      extraParams: { foo: "bar", skip: null },
      fetchInit: { headers: { "X-Test": "1" } }
    });
    const result = await fetcher({ page: 2 });
    const calledUrl = new URL(global.fetch.mock.calls[0][0]);
    expect(calledUrl.searchParams.get("p")).toBe("2");
    expect(calledUrl.searchParams.get("size")).toBe("20");
    expect(calledUrl.searchParams.get("foo")).toBe("bar");
    expect(result).toEqual({ html: "<p>hi</p>", hasMore: true, nextPage: 3 });
  });
}

function testSupportsCustomMapResponse() {
  test("supports custom mapResponse", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ body: "x" })
      })
    );
    const fetcher = buildJsonFetcher(window, {
      endpoint: "/api/custom",
      mapResponse: (json) => ({ html: json.body, hasMore: false, nextPage: null })
    });
    const result = await fetcher({ page: 1 });
    expect(result).toEqual({ html: "x", hasMore: false, nextPage: null });
  });
}

function testRejectsOnNonOkResponse() {
  test("falls back to global window and rejects on non-ok response", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false, json: () => Promise.resolve({}) }));
    const fetcher = buildJsonFetcher(null, { endpoint: "/api/fail" });
    await expect(fetcher({ page: 1 })).rejects.toThrow("Request failed");
  });
}

function testDefaultsMappingWhenJsonMissingFields() {
  test("defaults mapping when json missing fields", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    const fetcher = buildJsonFetcher(window, { endpoint: "/api/empty" });
    const result = await fetcher({ page: 0 });
    expect(result).toEqual({ html: "", hasMore: false, nextPage: undefined });
  });
}

function setupInfiniteListEnv() {
  document.body.innerHTML = `<div id="sentinel"></div>`;
  sentinel = document.getElementById("sentinel");
  fetchPage = jest.fn(() => Promise.resolve({ html: "<div></div>", hasMore: false, nextPage: null }));
  append = jest.fn();
  cleanupObservers = [];
  global.fetch = undefined;
}

function teardownInfiniteListEnv() {
  cleanupObservers.forEach((obs) => obs && obs.disconnect && obs.disconnect());
  delete global.IntersectionObserver;
}

function testReturnsNullWhenRequiredOptionsMissing() {
  test("returns null when required options missing or no more pages", () => {
    expect(createInfiniteList(window, null)).toBeNull();
    expect(createInfiniteList(window, { sentinel })).toBeNull();
    expect(createInfiniteList(window, { sentinel, fetchPage, append })).toBeNull();
    expect(
      createInfiniteList(window, { sentinel, fetchPage, append, hasMore: false, nextPage: 1 })
    ).toBeNull();
    expect(createInfiniteList(window, { sentinel, fetchPage, append, hasMore: true, nextPage: null })).toBeNull();
  });
}

function testUsesIntersectionObserver() {
  test("uses IntersectionObserver and disconnects when no more pages", async () => {
    const observed = [];
    let trigger;
    const MockObserver = function (cb) {
      const instance = {
        observe: (el) => observed.push(el),
        disconnect: jest.fn()
      };
      trigger = (isIntersecting = true) => cb([{ isIntersecting }]);
      cleanupObservers.push(instance);
      return instance;
    };
    global.IntersectionObserver = MockObserver;
    const list = createInfiniteList(window, { sentinel, fetchPage, append, hasMore: true, nextPage: 2 });
    expect(observed[0]).toBe(sentinel);
    trigger(true);
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchPage).toHaveBeenCalledWith({ page: 2 });
    expect(append).toHaveBeenCalledWith("<div></div>", { page: 2 });
    expect(cleanupObservers[0].disconnect).toHaveBeenCalled();
    list.disconnect();
  });
}

function testIgnoresNonIntersectingEntries() {
  test("ignores non-intersecting entries", () => {
    let trigger;
    global.IntersectionObserver = function (cb) {
      trigger = (isIntersecting = true) => cb([{ isIntersecting }]);
      return { observe: () => {}, disconnect: () => {} };
    };
    const list = createInfiniteList(window, { sentinel, fetchPage, append, hasMore: true, nextPage: 2 });
    trigger(false);
    expect(fetchPage).not.toHaveBeenCalled();
    list.disconnect();
  });
}

function testFallbackScrollSentinelTriggersFetch() {
  test("fallback scroll in sentinel mode triggers fetch", async () => {
    delete global.IntersectionObserver;
    const addSpy = jest.spyOn(window, "addEventListener");
    sentinel.getBoundingClientRect = () => ({ top: 0 });
    window.innerHeight = 100;
    const list = createInfiniteList(window, {
      sentinel,
      fetchPage,
      append,
      hasMore: true,
      nextPage: 5,
      fallbackScroll: true,
      fallbackMargin: 10
    });
    const handler = addSpy.mock.calls.find((c) => c[0] === "scroll")[1];
    handler();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchPage).toHaveBeenCalledWith({ page: 5 });
    list.disconnect();
    addSpy.mockRestore();
  });
}

function testFallbackScrollSkipsWhenAboveThreshold() {
  test("fallback scroll skips when sentinel above threshold", () => {
    delete global.IntersectionObserver;
    const addSpy = jest.spyOn(window, "addEventListener");
    Object.defineProperty(sentinel, "getBoundingClientRect", {
      value: () => ({ top: 1000 }),
      configurable: true
    });
    window.innerHeight = 100;
    const list = createInfiniteList(window, {
      sentinel,
      fetchPage,
      append,
      hasMore: true,
      nextPage: 6,
      fallbackScroll: true,
      fallbackMargin: 10
    });
    const handler = addSpy.mock.calls.find((c) => c[0] === "scroll")[1];
    handler();
    expect(fetchPage).not.toHaveBeenCalled();
    list.disconnect();
    addSpy.mockRestore();
  });
}

function testFallbackDocumentModeTriggersFetch() {
  test("fallback scroll in document mode triggers fetch when threshold passed", async () => {
    delete global.IntersectionObserver;
    const addSpy = jest.spyOn(window, "addEventListener");
    Object.defineProperty(document.body, "offsetHeight", { value: 1000, configurable: true });
    window.innerHeight = 500;
    window.scrollY = 600;
    const list = createInfiniteList(window, {
      sentinel,
      fetchPage,
      append,
      hasMore: true,
      nextPage: 3,
      fallbackScroll: true,
      fallbackMode: "document",
      fallbackMargin: 100
    });
    const handler = addSpy.mock.calls.find((c) => c[0] === "scroll")[1];
    handler();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchPage).toHaveBeenCalledWith({ page: 3 });
    list.disconnect();
    addSpy.mockRestore();
  });
}

function testTriggerHandlesRejection() {
  test("trigger manually calls fetchMore and clears loading on rejection", async () => {
    const failingFetcher = jest.fn(() => Promise.reject(new Error("fail")));
    const list = createInfiniteList(window, {
      sentinel,
      fetchPage: failingFetcher,
      append,
      hasMore: true,
      nextPage: 10,
      observerOptions: { root: null, threshold: 0.1 }
    });
    list.trigger();
    await new Promise((r) => setTimeout(r, 0));
    expect(failingFetcher).toHaveBeenCalled();
    list.disconnect();
  });
}

function testStopsFetchingWhenNoMorePages() {
  test("stops fetching when hasMore becomes false", async () => {
    fetchPage = jest
      .fn()
      .mockResolvedValueOnce({ html: null, hasMore: true, nextPage: 3 })
      .mockResolvedValueOnce({ html: null, hasMore: false, nextPage: null });
    let observerTrigger;
    global.IntersectionObserver = function (cb) {
      observerTrigger = (isIntersecting = true) => cb([{ isIntersecting }]);
      return { observe: () => {}, disconnect: jest.fn() };
    };
    const list = createInfiniteList(window, { sentinel, fetchPage, append, hasMore: true, nextPage: 2 });
    observerTrigger(true);
    await new Promise((r) => setTimeout(r, 0));
    observerTrigger(true);
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchPage).toHaveBeenCalledTimes(2);
    list.trigger();
    expect(fetchPage).toHaveBeenCalledTimes(2);
    list.disconnect();
  });
}

describe("placeInColumns", () => {
  test("appends nodes to shortest columns", () => {
    const col1 = document.createElement("div");
    const col2 = document.createElement("div");
    Object.defineProperty(col1, "offsetHeight", { value: 50 });
    Object.defineProperty(col2, "offsetHeight", { value: 10 });
    const nodeA = document.createElement("span");
    const nodeB = document.createElement("span");
    placeInColumns([nodeA, nodeB], [col1, col2]);
    expect(col2.contains(nodeA)).toBe(true);
    expect(col2.contains(nodeB)).toBe(true);
  });

  test("no-op when inputs missing", () => {
    expect(() => placeInColumns(null, null)).not.toThrow();
    placeInColumns([document.createElement("div")], []);
  });
});

describe("attachGlobal", () => {
  test("attaches helpers to provided window and invokes stubs", () => {
    const w = {};
    attachGlobal(w);
    expect(typeof w.InfiniteList.create).toBe("function");
    expect(typeof w.InfiniteList.buildJsonFetcher).toBe("function");
    expect(typeof w.InfiniteList.placeInColumns).toBe("function");
    expect(w.InfiniteList.create({})).toBeNull();
    expect(w.InfiniteList.buildJsonFetcher({ endpoint: "/x" })).not.toBeNull();
  });

  test("no-ops when window missing", () => {
    expect(() => attachGlobal(null)).not.toThrow();
  });
});
