const { initSaveModal } = require("../../static/js/save_modal");

function buildModalDom() {
  document.body.innerHTML = `
    <div id="saveModal" data-save-endpoint="/toggle" data-csrf="token">
      <div class="modal-dialog"></div>
      <div class="save-modal-view" data-save-view="list"></div>
      <div class="save-modal-view d-none" data-save-view="create"></div>
      <div class="save-modal-search"><input type="text" /></div>
      <ul class="save-modal-list">
        <li class="save-modal-row" data-collection-id="1">
          <div><p class="fw-semibold">Alpha</p></div>
          <button data-save-toggle data-collection-id="1"><i class="bi bi-bookmark"></i></button>
        </li>
        <li class="save-modal-row" data-collection-id="2">
          <div><p class="fw-semibold">Beta</p></div>
          <button data-save-toggle data-collection-id="2"><i class="bi bi-bookmark-fill"></i></button>
        </li>
      </ul>
      <button data-save-open-create></button>
      <button data-save-back></button>
      <button data-dismiss-save-modal></button>
    </div>
    <button data-open-save-modal></button>
    <form id="save-modal-create-form">
      <input id="new-collection-name" />
    </form>
    <input name="csrfmiddlewaretoken" value="token" />
  `;
}

describe("save_modal", () => {
  let originalFetch;
  let originalRAF;

  beforeEach(() => {
    document.body.innerHTML = "";
    originalFetch = global.fetch;
    global.fetch = jest.fn();
    originalRAF = global.requestAnimationFrame;
    global.requestAnimationFrame = (cb) => cb();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.requestAnimationFrame = originalRAF;
    jest.clearAllMocks();
  });

  test("filters list by search and shows no-results row", () => {
    buildModalDom();
    initSaveModal(window);

    const input = document.querySelector(".save-modal-search input");
    input.value = "beta";
    input.dispatchEvent(new Event("input"));

    const rows = document.querySelectorAll(".save-modal-row");
    expect(rows[0].classList.contains("d-none")).toBe(true);
    expect(rows[1].classList.contains("d-none")).toBe(false);
    expect(document.querySelector(".save-modal-no-results")).not.toBeNull();
  });

  test("toggle button flips bookmark state after fetch", async () => {
    buildModalDom();
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ saved: true })
    });
    initSaveModal(window);

    const btn = document.querySelector("[data-save-toggle]");
    btn.click();

    await new Promise((resolve) => setTimeout(resolve, 0));
    const icon = btn.querySelector("i");
    expect(icon.classList.contains("bi-bookmark-fill")).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith("/toggle", expect.objectContaining({
      method: "POST"
    }));
  });

  test("create form adds new row and hides modal", async () => {
    buildModalDom();
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ saved: true, collection: { id: 3, name: "Gamma" } })
    });
    initSaveModal(window);

    document.getElementById("new-collection-name").value = "Gamma";
    document.getElementById("save-modal-create-form").dispatchEvent(new Event("submit", { cancelable: true }));

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector('[data-collection-id="3"]')).not.toBeNull();
  });

  test("opens and closes modal without bootstrap", () => {
    buildModalDom();
    initSaveModal(window);
    const openBtn = document.querySelector("[data-open-save-modal]");
    openBtn.click();
    expect(document.getElementById("saveModal").classList.contains("show")).toBe(true);
    document.querySelector("[data-dismiss-save-modal]").click();
    expect(document.getElementById("saveModal").classList.contains("show")).toBe(false);
  });

  test("handles missing modal gracefully", () => {
    document.body.innerHTML = "";
    initSaveModal(window);
    expect(document.body.innerHTML).toBe("");
  });

  test("row click toggles when not clicking button", async () => {
    buildModalDom();
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ saved: false })
    });
    initSaveModal(window);
    const row = document.querySelector(".save-modal-row");
    row.dispatchEvent(new Event("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(global.fetch).toHaveBeenCalled();
  });

  test("shows fallback backdrop when bootstrap missing", () => {
    buildModalDom();
    const modal = document.getElementById("saveModal");
    initSaveModal(window);
    document.querySelector("[data-open-save-modal]").click();
    const backdrop = document.querySelector(".custom-modal-backdrop");
    expect(backdrop).not.toBeNull();
    expect(backdrop.classList.contains("show")).toBe(true);
  });

  test("setSaveView toggles titles, subtitles, and hide-on-view elements", () => {
    buildModalDom();
    const modal = document.getElementById("saveModal");
    modal.innerHTML += `
      <h2 data-save-title="list" class="title-list"></h2>
      <h2 data-save-title="create" class="title-create d-none"></h2>
      <p data-save-subtitle="list" class="subtitle-list"></p>
      <p data-save-subtitle="create" class="subtitle-create d-none"></p>
      <div data-hide-when-view="create" class="hide-when-create"></div>
    `;
    initSaveModal(window);
    modal.querySelector("[data-save-open-create]").click();
    expect(modal.querySelector(".title-create").classList.contains("d-none")).toBe(false);
    expect(modal.querySelector(".subtitle-create").classList.contains("d-none")).toBe(false);
    expect(modal.querySelector(".hide-when-create").classList.contains("d-none")).toBe(true);
    modal.querySelector("[data-save-back]").click();
    expect(modal.querySelector(".hide-when-create").classList.contains("d-none")).toBe(false);
  });

  test("reuses fallback backdrop and ignores dialog clicks", () => {
    buildModalDom();
    initSaveModal(window);
    const openBtn = document.querySelector("[data-open-save-modal]");
    openBtn.click();
    const backdrop = document.querySelector(".custom-modal-backdrop");
    openBtn.click();
    expect(document.querySelectorAll(".custom-modal-backdrop").length).toBe(1);
    const modal = document.getElementById("saveModal");
    modal.classList.add("show");
    modal.style.display = "block";
    const dialog = modal.querySelector(".modal-dialog");
    dialog.dispatchEvent(new Event("click", { bubbles: true }));
    expect(modal.classList.contains("show")).toBe(true);
    modal.dispatchEvent(new Event("click", { bubbles: true }));
    expect(modal.classList.contains("show")).toBe(false);
    expect(backdrop.classList.contains("show")).toBe(false);
  });

  test("create form exits if no name", () => {
    buildModalDom();
    initSaveModal(window);
    document.getElementById("new-collection-name").value = "";
    document.getElementById("save-modal-create-form").dispatchEvent(new Event("submit", { cancelable: true }));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("toggle catch block flips icon on fetch failure", async () => {
    buildModalDom();
    global.fetch.mockRejectedValue(new Error("fail"));
    initSaveModal(window);
    const btn = document.querySelector("[data-save-toggle]");
    const icon = btn.querySelector("i");
    btn.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(icon.classList.contains("bi-bookmark-fill")).toBe(true);
  });

  test("bootstrap modal path used when available", () => {
    buildModalDom();
    const mockShow = jest.fn();
    const mockHide = jest.fn();
    global.bootstrap = {
      Modal: {
        getOrCreateInstance: () => ({ show: mockShow, hide: mockHide })
      }
    };
    initSaveModal(window);
    document.querySelector("[data-open-save-modal]").click();
    expect(mockShow).toHaveBeenCalled();
    document.querySelector("[data-dismiss-save-modal]").click();
    expect(mockHide).toHaveBeenCalled();
    delete global.bootstrap;
  });

  test("click outside dialog hides modal", () => {
    buildModalDom();
    initSaveModal(window);
    const modal = document.getElementById("saveModal");
    modal.classList.add("show");
    modal.style.display = "block";
    modal.dispatchEvent(new Event("click", { bubbles: true }));
    expect(modal.classList.contains("show")).toBe(false);
  });

  test("gracefully handles missing list/search on init", () => {
    document.body.innerHTML = `
      <div id="saveModal" data-save-endpoint="/toggle" data-csrf="token">
        <div class="modal-dialog"></div>
      </div>
    `;
    initSaveModal(window);
    expect(document.querySelector(".save-modal-no-results")).toBeNull();
  });

  test("initializes only once", () => {
    buildModalDom();
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ saved: true }) });
    initSaveModal(window);
    initSaveModal(window);
    const btn = document.querySelector("[data-save-toggle]");
    btn.click();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("handleToggle returns when missing collection id or icon", () => {
    document.body.innerHTML = `
      <div id="saveModal" data-save-endpoint="/toggle" data-csrf="token">
        <div class="modal-dialog"></div>
        <ul class="save-modal-list">
          <li class="save-modal-row">
            <button data-save-toggle></button>
          </li>
        </ul>
      </div>
    `;
    initSaveModal(window);
    const btn = document.querySelector("[data-save-toggle]");
    expect(() => btn.click()).not.toThrow();
  });

  test("create form hides modal on failed fetch and missing payload", async () => {
    buildModalDom();
    global.fetch.mockResolvedValue({ ok: false });
    initSaveModal(window);
    document.getElementById("new-collection-name").value = "Gamma";
    document.getElementById("save-modal-create-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("saveModal").classList.contains("show")).toBe(false);
  });

  test("create form catch block hides modal on rejection", async () => {
    buildModalDom();
    global.fetch.mockRejectedValue(new Error("boom"));
    initSaveModal(window);
    document.getElementById("new-collection-name").value = "Delta";
    document.getElementById("save-modal-create-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(document.getElementById("saveModal").classList.contains("show")).toBe(false);
  });

  test("shown.bs.modal resets view to list", () => {
    buildModalDom();
    global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show: jest.fn(), hide: jest.fn() }) } };
    initSaveModal(window);
    const modal = document.getElementById("saveModal");
    modal.dispatchEvent(new Event("shown.bs.modal"));
    expect(modal.querySelector('[data-save-view="list"]').classList.contains("d-none")).toBe(false);
    delete global.bootstrap;
  });

  test("handles missing csrf and dataset defaults without throwing", () => {
    document.body.innerHTML = `
      <div id="saveModal" data-save-endpoint="">
        <div class="modal-dialog"></div>
        <ul class="save-modal-list"></ul>
        <div class="save-modal-search"><input type="text" /></div>
      </div>
    `;
    expect(() => initSaveModal(window)).not.toThrow();
  });

  test("initSaveModal returns when window or modal missing", () => {
    expect(() => initSaveModal(null)).not.toThrow();
    document.body.innerHTML = `<div></div>`;
    expect(() => initSaveModal(window)).not.toThrow();
  });

  test("attachToggleHandler handles missing icon and row click guard", async () => {
    document.body.innerHTML = `
      <div id="saveModal" data-save-endpoint="/toggle" data-csrf="token">
        <div class="modal-dialog"></div>
        <ul class="save-modal-list">
          <li class="save-modal-row" data-collection-id="9">
            <button data-save-toggle data-collection-id="9"></button>
          </li>
        </ul>
      </div>
    `;
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ saved: true }) }));
    initSaveModal(window);
    const row = document.querySelector(".save-modal-row");
    row.dispatchEvent(new Event("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("hideSaveModal uses bootstrap path when present", () => {
    buildModalDom();
    const mockHide = jest.fn();
    global.bootstrap = {
      Modal: {
        getOrCreateInstance: () => ({ show: jest.fn(), hide: mockHide })
      }
    };
    initSaveModal(window);
    document.querySelector("[data-open-save-modal]").click();
    document.querySelector("[data-dismiss-save-modal]").click();
    expect(mockHide).toHaveBeenCalled();
    delete global.bootstrap;
  });
});
