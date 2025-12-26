function buildForm({ bound = false, hasErrors = false } = {}) {
  document.body.innerHTML = `
    <div class="create-recipe-card">
      <form data-form-bound="${bound ? "true" : "false"}" data-form-has-errors="${hasErrors ? "true" : "false"}">
        <div class="mb-3">
          <input id="title" required />
        </div>
        <div class="mb-3">
          <input id="id_images" type="file" />
          <div class="invalid-feedback">invalid</div>
          <div id="image-file-list"></div>
        </div>
        <div class="mb-3 shopping-links-field">
          <input id="shop-item" />
        </div>
        <div class="mb-3 shopping-links-upload">
          <input id="id_shop_images" type="file" />
          <div id="shop-image-file-list"></div>
        </div>
        <div class="mb-3 shopping-links-field">
          <input id="shop-link" />
        </div>
        <textarea id="id_ingredients_text"></textarea>
        <textarea id="id_shopping_links_text"></textarea>
        <button id="add-shop-link" type="button"></button>
        <div id="shop-list"></div>
      </form>
    </div>
  `;
}

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

function mockFiles(input, files) {
  Object.defineProperty(input, "files", { value: files, configurable: true });
}

function registerDomHooks() {
  let originalCreateObjectURL;
  let originalRevokeObjectURL;
  let originalFetch;
  let originalFileReader;

  beforeEach(() => {
    document.body.innerHTML = "";
    sessionStorage.clear();
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    originalFetch = global.fetch;
    const defaultFileReader = class {
      constructor() {
        this.onload = null;
        this.onerror = null;
        this.result = null;
      }
      readAsDataURL() {
        if (this.onerror) this.onerror(new Error("noop"));
      }
    };
    originalFileReader = defaultFileReader;
    window.FileReader = defaultFileReader;
    URL.createObjectURL = jest.fn(() => "blob:preview");
    URL.revokeObjectURL = jest.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    global.fetch = originalFetch;
    window.FileReader = originalFileReader;
    jest.resetAllMocks();
  });
}

module.exports = {
  buildForm,
  flushPromises,
  mockFiles,
  registerDomHooks
};
