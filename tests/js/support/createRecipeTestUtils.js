const baseFormTemplate = (boundValue, errorValue) =>
  `<div class="create-recipe-card"><form data-form-bound="${boundValue}" data-form-has-errors="${errorValue}"><div class="mb-3"><input id="title" required /></div><div class="mb-3"><input id="id_images" type="file" /><div class="invalid-feedback">invalid</div><div id="image-file-list"></div></div><div class="mb-3 shopping-links-field"><input id="shop-item" /></div><div class="mb-3 shopping-links-upload"><input id="id_shop_images" type="file" /><div id="shop-image-file-list"></div></div><div class="mb-3 shopping-links-field"><input id="shop-link" /></div><textarea id="id_ingredients_text"></textarea><textarea id="id_shopping_links_text"></textarea><button id="add-shop-link" type="button"></button><div id="shop-list"></div></form></div>`;

function buildForm({ bound = false, hasErrors = false } = {}) {
  const boundValue = bound ? "true" : "false";
  const errorValue = hasErrors ? "true" : "false";
  document.body.innerHTML = baseFormTemplate(boundValue, errorValue);
}

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

function mockFiles(input, files) {
  Object.defineProperty(input, "files", { value: files, configurable: true });
}

class TestFileReader {
  constructor() {
    this.onload = null;
    this.onerror = null;
    this.result = null;
  }

  readAsDataURL() {
    if (this.onerror) this.onerror(new Error("noop"));
  }
}

let originalCreateObjectURL;
let originalRevokeObjectURL;
let originalFetch;
let originalFileReader;

function registerDomHooks() {
  beforeEach(setupDomHooksEnv);
  afterEach(teardownDomHooksEnv);
}

function setupDomHooksEnv() {
  document.body.innerHTML = "";
  sessionStorage.clear();
  originalCreateObjectURL = URL.createObjectURL;
  originalRevokeObjectURL = URL.revokeObjectURL;
  originalFetch = global.fetch;
  originalFileReader = window.FileReader;
  window.FileReader = TestFileReader;
  URL.createObjectURL = jest.fn(() => "blob:preview");
  URL.revokeObjectURL = jest.fn();
}

function teardownDomHooksEnv() {
  URL.createObjectURL = originalCreateObjectURL;
  URL.revokeObjectURL = originalRevokeObjectURL;
  global.fetch = originalFetch;
  window.FileReader = originalFileReader;
  jest.resetAllMocks();
}

module.exports = {
  buildForm,
  flushPromises,
  mockFiles,
  registerDomHooks
};
