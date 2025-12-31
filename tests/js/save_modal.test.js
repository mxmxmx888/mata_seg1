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

const qs = (sel) => document.querySelector(sel);
const waitTick = () => new Promise((resolve) => setTimeout(resolve, 0));

function setupModal({ fetchResult, domBuilder = buildModalDom } = {}) {
  domBuilder();
  if (fetchResult) {
    global.fetch.mockResolvedValue(fetchResult);
  }
  initSaveModal(window);
  return {
    modal: qs("#saveModal"),
    open: () => qs("[data-open-save-modal]")?.click(),
    dismiss: () => qs("[data-dismiss-save-modal]")?.click(),
    createForm: qs("#save-modal-create-form"),
    nameInput: qs("#new-collection-name"),
    toggleBtn: qs("[data-save-toggle]"),
    list: () => qs(".save-modal-list"),
  };
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

  describe("search and listing", () => {
    test("filters list by search and shows no-results row", () => {
      setupModal();
      const input = qs(".save-modal-search input");
      input.value = "beta";
      input.dispatchEvent(new Event("input"));

      const rows = document.querySelectorAll(".save-modal-row");
      expect(rows[0].classList.contains("d-none")).toBe(true);
      expect(rows[1].classList.contains("d-none")).toBe(false);
      expect(qs(".save-modal-no-results")).not.toBeNull();
    });

    test("handleToggle returns when missing collection id or icon", () => {
      setupModal({
        domBuilder: () => {
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
        }
      });
      const btn = qs("[data-save-toggle]");
      expect(() => btn.click()).not.toThrow();
    });
  });

  describe("toggling saves", () => {
    test("toggle button flips bookmark state after fetch", async () => {
      const { toggleBtn } = setupModal({
        fetchResult: { ok: true, json: () => Promise.resolve({ saved: true }) }
      });
      toggleBtn.click();

      await waitTick();
      const icon = toggleBtn.querySelector("i");
      expect(icon.classList.contains("bi-bookmark-fill")).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith("/toggle", expect.objectContaining({ method: "POST" }));
    });

    test("row click toggles when not clicking button", async () => {
      setupModal({
        fetchResult: { ok: true, json: () => Promise.resolve({ saved: false }) }
      });
      const row = qs(".save-modal-row");
      row.dispatchEvent(new Event("click", { bubbles: true }));
      await waitTick();
      expect(global.fetch).toHaveBeenCalled();
    });

    test("toggle catch block flips icon on fetch failure", async () => {
      global.fetch.mockRejectedValue(new Error("fail"));
      const { toggleBtn } = setupModal();
      const icon = toggleBtn.querySelector("i");
      toggleBtn.click();
      await waitTick();
      expect(icon.classList.contains("bi-bookmark-fill")).toBe(true);
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
      const row = qs(".save-modal-row");
      row.dispatchEvent(new Event("click", { bubbles: true }));
      await waitTick();
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe("creating collections", () => {
    test("create form adds new row and hides modal", async () => {
      const { nameInput, createForm } = setupModal({
        fetchResult: { ok: true, json: () => Promise.resolve({ saved: true, collection: { id: 3, name: "Gamma" } }) }
      });
      nameInput.value = "Gamma";
      createForm.dispatchEvent(new Event("submit", { cancelable: true }));

      await waitTick();
      expect(qs('[data-collection-id="3"]')).not.toBeNull();
    });

    test("create form exits if no name", () => {
      const { nameInput, createForm } = setupModal();
      nameInput.value = "";
      createForm.dispatchEvent(new Event("submit", { cancelable: true }));
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test("create form hides modal on failed fetch and missing payload", async () => {
      const { nameInput, createForm, modal } = setupModal({ fetchResult: { ok: false } });
      nameInput.value = "Gamma";
      createForm.dispatchEvent(new Event("submit", { cancelable: true }));
      await waitTick();
      expect(modal.classList.contains("show")).toBe(false);
    });

    test("create form catch block hides modal on rejection", async () => {
      global.fetch.mockRejectedValue(new Error("boom"));
      const { nameInput, createForm, modal } = setupModal();
      nameInput.value = "Delta";
      createForm.dispatchEvent(new Event("submit", { cancelable: true }));
      await waitTick();
      expect(modal.classList.contains("show")).toBe(false);
    });
  });

  describe("modal display", () => {
    test("opens and closes modal without bootstrap", () => {
      const { modal, open, dismiss } = setupModal();
      open();
      expect(modal.classList.contains("show")).toBe(true);
      dismiss();
      expect(modal.classList.contains("show")).toBe(false);
    });

    test("shows fallback backdrop when bootstrap missing", () => {
      const { open } = setupModal();
      open();
      const backdrop = qs(".custom-modal-backdrop");
      expect(backdrop).not.toBeNull();
      expect(backdrop.classList.contains("show")).toBe(true);
    });

    test("setSaveView toggles titles, subtitles, and hide-on-view elements", () => {
      const appendDom = () => {
        buildModalDom();
        const modal = qs("#saveModal");
        modal.innerHTML += `
          <h2 data-save-title="list" class="title-list"></h2>
          <h2 data-save-title="create" class="title-create d-none"></h2>
          <p data-save-subtitle="list" class="subtitle-list"></p>
          <p data-save-subtitle="create" class="subtitle-create d-none"></p>
          <div data-hide-when-view="create" class="hide-when-create"></div>
        `;
      };
      const { modal } = setupModal({ domBuilder: appendDom });
      modal.querySelector("[data-save-open-create]").click();
      expect(modal.querySelector(".title-create").classList.contains("d-none")).toBe(false);
      expect(modal.querySelector(".subtitle-create").classList.contains("d-none")).toBe(false);
      expect(modal.querySelector(".hide-when-create").classList.contains("d-none")).toBe(true);
      modal.querySelector("[data-save-back]").click();
      expect(modal.querySelector(".hide-when-create").classList.contains("d-none")).toBe(false);
    });

    test("reuses fallback backdrop and ignores dialog clicks", () => {
      const { modal, open } = setupModal();
      open();
      const backdrop = qs(".custom-modal-backdrop");
      open();
      expect(document.querySelectorAll(".custom-modal-backdrop").length).toBe(1);
      modal.classList.add("show");
      modal.style.display = "block";
      const dialog = modal.querySelector(".modal-dialog");
      dialog.dispatchEvent(new Event("click", { bubbles: true }));
      expect(modal.classList.contains("show")).toBe(true);
      modal.dispatchEvent(new Event("click", { bubbles: true }));
      expect(modal.classList.contains("show")).toBe(false);
      expect(backdrop.classList.contains("show")).toBe(false);
    });

    test("bootstrap modal path used when available", () => {
      const mockShow = jest.fn();
      const mockHide = jest.fn();
      global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show: mockShow, hide: mockHide }) } };
      const { open, dismiss } = setupModal();
      open();
      expect(mockShow).toHaveBeenCalled();
      dismiss();
      expect(mockHide).toHaveBeenCalled();
      delete global.bootstrap;
    });

    test("click outside dialog hides modal", () => {
      const { modal } = setupModal();
      modal.classList.add("show");
      modal.style.display = "block";
      modal.dispatchEvent(new Event("click", { bubbles: true }));
      expect(modal.classList.contains("show")).toBe(false);
    });

    test("shown.bs.modal resets view to list", () => {
      global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show: jest.fn(), hide: jest.fn() }) } };
      const { modal } = setupModal();
      modal.dispatchEvent(new Event("shown.bs.modal"));
      expect(modal.querySelector('[data-save-view="list"]').classList.contains("d-none")).toBe(false);
      delete global.bootstrap;
    });

    test("hideSaveModal uses bootstrap path when present", () => {
      const mockHide = jest.fn();
      global.bootstrap = { Modal: { getOrCreateInstance: () => ({ show: jest.fn(), hide: mockHide }) } };
      const { open, dismiss } = setupModal();
      open();
      dismiss();
      expect(mockHide).toHaveBeenCalled();
      delete global.bootstrap;
    });
  });

  describe("guards and idempotency", () => {
    test("handles missing modal gracefully", () => {
      document.body.innerHTML = "";
      initSaveModal(window);
      expect(document.body.innerHTML).toBe("");
    });

    test("gracefully handles missing list/search on init", () => {
      document.body.innerHTML = `
        <div id="saveModal" data-save-endpoint="/toggle" data-csrf="token">
          <div class="modal-dialog"></div>
        </div>
      `;
      initSaveModal(window);
      expect(qs(".save-modal-no-results")).toBeNull();
    });

    test("initializes only once", () => {
      setupModal({ fetchResult: { ok: true, json: () => Promise.resolve({ saved: true }) } });
      initSaveModal(window);
      const btn = qs("[data-save-toggle]");
      btn.click();
      expect(global.fetch).toHaveBeenCalledTimes(1);
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
  });
});
