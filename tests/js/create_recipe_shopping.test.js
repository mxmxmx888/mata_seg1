const { createShoppingManager } = require("../../static/js/create_recipe_shopping");

const createFocusInput = (type = "input", extraProps = {}) =>
  Object.assign(document.createElement(type), { focus: jest.fn(), ...extraProps });

function wrapField(className, el) {
  const div = document.createElement("div");
  div.className = className;
  div.appendChild(el);
  document.body.appendChild(div);
  return div;
}

function createWindowStubs(dtFiles) {
  return {
    URL: { createObjectURL: jest.fn(() => "blob:preview"), revokeObjectURL: jest.fn() },
    DataTransfer: class {
      constructor() {
        this.items = { add: (f) => dtFiles.push(f) };
        this.files = dtFiles;
      }
    }
  };
}

const buildParams = (overrides = {}) => {
  const itemInput = createFocusInput();
  const linkInput = createFocusInput();
  const shopImageInput = createFocusInput("input", { type: "file" });
  const shoppingField = document.createElement("textarea");
  const listBox = document.createElement("div");
  const shopImageList = document.createElement("div");
  const addBtn = document.createElement("button");
  const itemWrapper = wrapField("shopping-links-field", itemInput);
  const linkWrapper = wrapField("shopping-links-field", linkInput);
  const uploadWrapper = wrapField("shopping-links-upload", shopImageInput);
  document.body.append(listBox);
  const dtFiles = [];
  return { w: createWindowStubs(dtFiles), doc: document, addBtn, itemInput, linkInput, shopImageInput, itemWrapper, linkWrapper, uploadWrapper, shopImageList, shoppingField, listBox, setInputFiles: jest.fn(), getFiles: jest.fn(() => []), normalizeUrl: (url) => (url.startsWith("http") ? url : `https://${url}`), ...overrides };
};

afterEach(() => {
  jest.resetModules();
  jest.clearAllMocks();
});

test("shows errors and focuses first missing field", () => {
  const params = buildParams();
  createShoppingManager(params).addLink();
  expect(params.itemInput.focus).toHaveBeenCalled();
  expect(document.querySelectorAll(".client-required-error").length).toBe(3);
});

test("adds link, normalizes url, renders list, and remove works", () => {
  const params = buildParams({ getFiles: jest.fn(() => [{ name: "pic.png" }]) });
  params.itemInput.value = "Milk";
  params.linkInput.value = "shop.com";
  const manager = createShoppingManager(params);
  manager.addLink();
  expect(params.w.URL.createObjectURL).toHaveBeenCalled();
  expect(params.shoppingField.value).toContain("Milk | https://shop.com");
  expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(1);
  params.listBox.querySelector(".remove").click();
  expect(params.listBox.textContent).toContain("No shopping links added yet.");
  expect(params.shoppingField.value).toBe("");
});

test("bind handles Enter submit, shop image change, and clears errors on input", () => {
  const params = buildParams({ getFiles: jest.fn(() => [{ name: "x.png" }]) });
  const manager = createShoppingManager(params);
  manager.bind();
  params.itemInput.value = "Eggs";
  params.linkInput.value = "eggs.com";
  params.shopImageInput.dispatchEvent(new Event("change"));
  params.linkInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
  expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(1);
  params.itemInput.value = "";
  manager.addLink();
  expect(params.itemWrapper.querySelector(".client-required-error")).not.toBeNull();
  params.itemInput.dispatchEvent(new Event("input"));
  expect(params.itemWrapper.querySelector(".client-required-error")).toBeNull();
});

test("shop image change renders preview and remove clears pending", () => {
  const params = buildParams({ getFiles: jest.fn(() => [{ name: "preview.png" }]) });
  const manager = createShoppingManager(params);
  manager.bind();
  params.shopImageInput.dispatchEvent(new Event("change"));
  expect(params.shopImageList.querySelector(".image-preview-item")).not.toBeNull();
  params.shopImageList.querySelector(".image-remove").click();
  expect(params.shopImageList.innerHTML).toBe("");
});

test("limits shopping links to 10 and clears limit error after removal", () => {
  const params = buildParams({ getFiles: jest.fn(() => [{ name: "pic.png" }]) });
  const manager = createShoppingManager(params);
  for (let i = 0; i < 10; i += 1) {
    params.itemInput.value = `Item ${i}`;
    params.linkInput.value = `item${i}.com`;
    manager.addLink();
  }
  expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(10);
  params.itemInput.value = "Extra";
  params.linkInput.value = "extra.com";
  manager.addLink();
  expect(params.itemWrapper.querySelector(".client-required-error").textContent).toMatch(/up to 10/i);
  params.listBox.querySelector(".remove").click();
  expect(params.itemWrapper.querySelector(".client-required-error")).toBeNull();
});

test("bootstrapExisting parses textarea lines and existing items", () => {
  const params = buildParams({
    shoppingField: document.createElement("textarea"),
    existingShoppingItems: [{ name: "Bread", url: "http://bread.com", image_url: "http://bread.com/img" }]
  });
  params.shoppingField.value = "Milk | http://milk.com\nCheese | cheese.com";
  const manager = createShoppingManager(params);
  manager.bootstrapExisting();
  manager.renderList();
  expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(2);

  const params2 = buildParams({
    shoppingField: document.createElement("textarea"),
    existingShoppingItems: [{ name: "Bread", url: "http://bread.com", image_url: "http://bread.com/img" }]
  });
  const manager2 = createShoppingManager(params2);
  manager2.bootstrapExisting();
  manager2.renderList();
  expect(params2.listBox.querySelectorAll(".shopping-list-item").length).toBe(1);
});
