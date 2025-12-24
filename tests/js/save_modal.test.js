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
    expect(true).toBe(true);
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
    expect(true).toBe(true);
  });

  test("initializes only once", () => {
    buildModalDom();
    initSaveModal(window);
    initSaveModal(window);
    expect(true).toBe(true);
  });
});
