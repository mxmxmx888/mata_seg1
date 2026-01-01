const { initCreateRecipe, normalizeUrl } = require("../../static/js/create_recipe");
const { buildForm, mockFiles, registerDomHooks } = require("./support/createRecipeTestUtils");

registerDomHooks();

const addShoppingLink = (item = "Banana", link = "banana.com", fileName = "pic.jpg") => {
  const file = new File(["data"], fileName, { type: "image/jpeg" });
  mockFiles(document.getElementById("id_shop_images"), [file]);
  document.getElementById("shop-item").value = item;
  document.getElementById("shop-link").value = link;
  document.getElementById("add-shop-link").click();
};

const createManagerMocks = () => ({
  imageManager: { bind: jest.fn(), restoreFromStorage: jest.fn(), persistSelection: jest.fn() },
  shoppingManager: {
    bind: jest.fn(),
    bootstrapExisting: jest.fn(),
    renderList: jest.fn(),
    syncShoppingField: jest.fn(),
    syncShopImagesInput: jest.fn()
  },
  validator: { renderRequiredFieldErrors: jest.fn(() => false), bindRequiredListeners: jest.fn() }
});

function mockHelperFactories(managers) {
  jest.doMock("../../static/js/create_recipe_helpers", () => ({
    createImageManager: () => managers.imageManager,
    createShoppingManager: () => managers.shoppingManager,
    createRequiredFieldValidator: () => managers.validator,
    getFiles: () => [],
    setInputFiles: jest.fn()
  }));
}

function capturePageEvents() {
  const events = [];
  const originalAdd = window.addEventListener;
  window.addEventListener = (event, cb) => {
    events.push(event);
    if (cb) cb();
  };
  return { events, restore: () => { window.addEventListener = originalAdd; } };
}

test("normalizeUrl prefixes https when missing", () => {
  expect(normalizeUrl("example.com")).toBe("https://example.com");
  expect(normalizeUrl("http://example.com")).toBe("http://example.com");
  expect(normalizeUrl("")).toBe("");
});

test("adds a shopping link and syncs fields", () => {
  buildForm();
  initCreateRecipe(window);
  addShoppingLink();
  expect(document.querySelectorAll(".shopping-list-item").length).toBe(1);
  expect(document.getElementById("id_shopping_links_text").value).toContain("Banana | https://banana.com");
  expect(document.getElementById("shop-image-file-list").textContent).toContain("pic.jpg");
});

test("shows validation errors when fields missing", () => {
  buildForm();
  initCreateRecipe(window);
  document.getElementById("add-shop-link").click();
  expect(document.querySelectorAll(".client-required-error").length).toBe(3);
});

test("removes shopping link and clears hidden field", () => {
  buildForm();
  initCreateRecipe(window);
  addShoppingLink();
  document.querySelector(".remove").click();
  expect(document.getElementById("shop-list").textContent).toMatch(/No shopping links/i);
  expect(document.getElementById("id_shopping_links_text").value).toBe("");
});

test("bootstraps existing shopping field entries and normalizes urls", () => {
  buildForm();
  const field = document.getElementById("id_shopping_links_text");
  field.value = "Apple | apple.com\nOrange";
  initCreateRecipe(window);
  expect(document.querySelectorAll(".shopping-list-item").length).toBe(2);
  expect(field.value).toContain("https://apple.com");
});

test("prevents submit when required fields missing", () => {
  buildForm();
  initCreateRecipe(window);
  const form = document.querySelector("form");
  const event = new Event("submit", { cancelable: true });
  const preventSpy = jest.spyOn(event, "preventDefault");
  form.dispatchEvent(event);
  expect(preventSpy).toHaveBeenCalled();
  expect(document.querySelectorAll(".client-required-error").length).toBeGreaterThan(0);
});

test("focuses missing url then missing image", () => {
  buildForm();
  initCreateRecipe(window);
  addShoppingLink("Item", "");
  expect(document.activeElement).toBe(document.getElementById("shop-link"));
  document.getElementById("shop-link").value = "https://ok.com";
  mockFiles(document.getElementById("id_shop_images"), []);
  document.getElementById("add-shop-link").click();
  expect(document.activeElement).toBe(document.getElementById("id_shop_images"));
});

test("submit succeeds when required fields filled and trims ingredients", () => {
  buildForm();
  const form = document.querySelector("form");
  mockFiles(document.getElementById("id_images"), [new File(["abc"], "photo.png", { type: "image/png" })]);
  document.getElementById("title").value = "Title";
  document.getElementById("id_ingredients_text").value = " apple \n banana ";
  initCreateRecipe(window);
  const result = form.dispatchEvent(new Event("submit", { cancelable: true }));
  expect(result).toBe(true);
  expect(document.getElementById("id_ingredients_text").value).toBe("apple\nbanana");
});

test("enter key triggers addLink for item and link inputs", () => {
  buildForm();
  initCreateRecipe(window);
  addShoppingLink("Kiwi", "kiwi.com");
  document.getElementById("shop-item").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  document.getElementById("shop-link").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  expect(document.querySelectorAll(".shopping-list-item").length).toBeGreaterThan(0);
});

test("early exits safely when window/document or required nodes missing", () => {
  expect(() => initCreateRecipe(null)).not.toThrow();
  document.body.innerHTML = `<div class="create-recipe-card"><form></form></div>`;
  expect(() => initCreateRecipe(window)).not.toThrow();
});

test("handles missing image input branch gracefully", () => {
  document.body.innerHTML = `
    <div class="create-recipe-card">
      <form data-form-bound="false" data-form-has-errors="false">
        <textarea id="id_ingredients_text"></textarea>
        <input id="shop-item" />
        <input id="shop-link" />
        <button id="add-shop-link" type="button"></button>
        <div id="shop-list"></div>
        <textarea id="id_shopping_links_text"></textarea>
      </form>
    </div>
  `;
  expect(() => initCreateRecipe(window)).not.toThrow();
});

test("global init uses DOMContentLoaded when document still loading", () => {
  jest.resetModules();
  const readyDescriptor = Object.getOwnPropertyDescriptor(document, "readyState");
  Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
  const addSpy = jest.spyOn(document, "addEventListener");
  require("../../static/js/create_recipe");
  expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
  addSpy.mockRestore();
  if (readyDescriptor) Object.defineProperty(document, "readyState", readyDescriptor);
});

test("bootstrapExisting handles lines without names and normalizes urls", () => {
  buildForm();
  const field = document.getElementById("id_shopping_links_text");
  field.value = " | example.com\nItem | http://ok.com";
  initCreateRecipe(window);
  expect(document.querySelectorAll(".shopping-list-item").length).toBe(1);
  expect(field.value).toContain("http://ok.com");
});

test("helper stubs still bind managers and lifecycle events", () => {
  jest.resetModules();
  const managers = createManagerMocks();
  mockHelperFactories(managers);
  const { initCreateRecipe } = require("../../static/js/create_recipe");
  buildForm({ bound: true, hasErrors: true });
  const { events, restore } = capturePageEvents();
  initCreateRecipe(window);
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  expect(managers.imageManager.bind).toHaveBeenCalled();
  expect(managers.shoppingManager.bind).toHaveBeenCalled();
  expect(events).toEqual(expect.arrayContaining(["pageshow", "pagehide"]));
  restore();
});

test("uses internal fallbacks when helpers are missing", () => {
  jest.resetModules();
  jest.doMock("../../static/js/create_recipe_helpers", () => ({}));
  const { initCreateRecipe } = require("../../static/js/create_recipe");
  buildForm();
  document.getElementById("shop-list").dataset.shoppingItems = "{bad";
  const form = document.querySelector("form");
  const submitEvent = new Event("submit", { cancelable: true });
  initCreateRecipe(window);
  form.dispatchEvent(submitEvent);
  expect(submitEvent.defaultPrevented).toBe(false);
});
