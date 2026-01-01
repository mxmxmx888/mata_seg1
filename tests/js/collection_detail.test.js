const modulePath = "../../static/js/collection_detail";

function loadModule() {
  jest.resetModules();
  delete global.__collectionDetailInitialized;
  const mod = require(modulePath);
  delete global.__collectionDetailInitialized;
  return mod;
}

let originalFetch;
let originalLocation;

describe("collection_detail", () => {
  beforeEach(setupCollectionDetailEnv);
  afterEach(teardownCollectionDetailEnv);
  testShowsModalAndUpdatesTitle();
  testFallbackModalTogglesClasses();
  testCloseButtonHidesFallbackModal();
  testDeleteConfirmsAndRedirects();
  testCancelDeleteAndEmptyTitle();
  testHandlesMissingBootstrapInstance();
  testEditSubmitHandlesFetchFailure();
  testDeleteFetchFailureStillRedirects();
  testEditSubmitRejectsAndHides();
  testEarlyExitsWhenMissingRequirements();
});

function setupCollectionDetailEnv() {
  document.body.innerHTML = "";
  originalFetch = global.fetch;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ title: "Updated" }) }));
  originalLocation = global.location;
  delete global.location;
  global.location = { href: "" };
}

function teardownCollectionDetailEnv() {
  global.fetch = originalFetch;
  global.location = originalLocation;
  delete global.bootstrap;
  jest.clearAllMocks();
}

function buildDom() {
  document.body.innerHTML = `
      <input name="csrfmiddlewaretoken" value="token" />
      <button id="edit-collection-button" data-collection-id="abc" data-collection-title="Old" data-edit-endpoint="/edit"></button>
      <button id="delete-collection-button" data-delete-endpoint="/delete" data-redirect-url="/collections"></button>
      <div class="collection-title">Old</div>
      <div id="editCollectionModal" aria-hidden="true">
        <button class="save-modal-close"></button>
        <form id="edit-collection-form">
          <input id="edit-collection-title" value="Old" />
        </form>
      </div>
    `;
}

function testShowsModalAndUpdatesTitle() {
  test("shows modal and updates title via bootstrap path", async () => {
    buildDom();
    const show = jest.fn();
    global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show, hide: jest.fn() }) } };
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);

    document.getElementById("edit-collection-button").click();
    expect(show).toHaveBeenCalled();

    const form = document.getElementById("edit-collection-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledWith("/edit", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "X-CSRFToken": "token" })
    }));
    expect(document.querySelector(".collection-title").textContent).toBe("Updated");
  });
}

function testFallbackModalTogglesClasses() {
  test("fallback modal toggles classes without bootstrap", () => {
    buildDom();
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);

    document.getElementById("edit-collection-button").click();
    const modal = document.getElementById("editCollectionModal");
    expect(modal.classList.contains("show")).toBe(true);

    modal.click();
    expect(modal.classList.contains("show")).toBe(false);
  });
}

function testCloseButtonHidesFallbackModal() {
  test("close button hides fallback modal", () => {
    buildDom();
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);

    const modal = document.getElementById("editCollectionModal");
    document.getElementById("edit-collection-button").click();
    modal.querySelector(".save-modal-close").click();
    expect(modal.classList.contains("show")).toBe(false);
  });
}

function testDeleteConfirmsAndRedirects() {
  test("delete confirms and redirects", async () => {
    buildDom();
    global.confirm = jest.fn(() => true);
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);

    document.getElementById("delete-collection-button").click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledWith("/delete", expect.any(Object));
    expect(global.location.href).toBe("/collections");
  });
}

function testCancelDeleteAndEmptyTitle() {
  test("cancel delete does nothing and empty title aborts submit", async () => {
    buildDom();
    global.confirm = jest.fn(() => false);
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);

    document.getElementById("delete-collection-button").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).not.toHaveBeenCalledWith("/delete", expect.any(Object));

    const input = document.getElementById("edit-collection-title");
    input.value = " ";
    const form = document.getElementById("edit-collection-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).not.toHaveBeenCalledWith("/edit", expect.any(Object));
  });
}

function testHandlesMissingBootstrapInstance() {
  test("handles missing bootstrap modal instance gracefully", () => {
    buildDom();
    global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show: jest.fn(), hide: jest.fn() }) } };
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);
    expect(() => document.getElementById("edit-collection-button").click()).not.toThrow();
  });
}

function testEditSubmitHandlesFetchFailure() {
  test("edit submit handles fetch failure", async () => {
    buildDom();
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);
    const form = document.getElementById("edit-collection-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).toHaveBeenCalledWith("/edit", expect.any(Object));
  });
}

function testDeleteFetchFailureStillRedirects() {
  test("delete fetch failure still redirects", async () => {
    buildDom();
    global.confirm = jest.fn(() => true);
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);
    document.getElementById("delete-collection-button").click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.location.href).toBe("/collections");
  });
}

function testEditSubmitRejectsAndHides() {
  test("edit submit rejects and triggers hideEditModal catch", async () => {
    buildDom();
    global.fetch = jest.fn(() => Promise.reject(new Error("fail")));
    const { initCollectionDetail } = loadModule();
    initCollectionDetail(window);
    const modal = document.getElementById("editCollectionModal");
    modal.classList.add("show");
    const form = document.getElementById("edit-collection-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(modal.classList.contains("show")).toBe(false);
  });
}

function testEarlyExitsWhenMissingRequirements() {
  test("early exits when missing required elements or already initialized", () => {
    document.body.innerHTML = ``;
    const { initCollectionDetail } = loadModule();
    expect(() => initCollectionDetail(window)).not.toThrow();
    window.__collectionDetailInitialized = true;
    expect(() => initCollectionDetail(window)).not.toThrow();
    delete window.__collectionDetailInitialized;
  });
}
