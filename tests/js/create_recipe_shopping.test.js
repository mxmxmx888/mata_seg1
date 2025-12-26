const { createShoppingManager } = require("../../static/js/create_recipe_shopping");

function buildParams(overrides = {}) {
  const itemInput = document.createElement("input");
  itemInput.focus = jest.fn();
  const linkInput = document.createElement("input");
  linkInput.focus = jest.fn();
  const shopImageInput = document.createElement("input");
  shopImageInput.type = "file";
  shopImageInput.focus = jest.fn();
  const shoppingField = document.createElement("textarea");
  const listBox = document.createElement("div");
  const shopImageList = document.createElement("div");
  const addBtn = document.createElement("button");
  const itemWrapper = document.createElement("div");
  itemWrapper.className = "shopping-links-field";
  itemWrapper.appendChild(itemInput);
  const linkWrapper = document.createElement("div");
  linkWrapper.className = "shopping-links-field";
  linkWrapper.appendChild(linkInput);
  const uploadWrapper = document.createElement("div");
  uploadWrapper.className = "shopping-links-upload";
  uploadWrapper.appendChild(shopImageInput);
  document.body.appendChild(itemWrapper);
  document.body.appendChild(linkWrapper);
  document.body.appendChild(uploadWrapper);
  document.body.appendChild(listBox);
  const dtFiles = [];
  const w = {
    URL: {
      createObjectURL: jest.fn(() => "blob:preview"),
      revokeObjectURL: jest.fn()
    },
    DataTransfer: class {
      constructor() {
        this.items = { add: (f) => dtFiles.push(f) };
        this.files = dtFiles;
      }
    }
  };

  return {
    w,
    doc: document,
    addBtn,
    itemInput,
    linkInput,
    shopImageInput,
    itemWrapper,
    linkWrapper,
    uploadWrapper,
    shopImageList,
    shoppingField,
    listBox,
    setInputFiles: jest.fn(),
    getFiles: jest.fn(() => []),
    normalizeUrl: (url) => (url.startsWith("http") ? url : `https://${url}`),
    ...overrides
  };
}

describe("create_recipe_shopping", () => {
  afterEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  test("shows errors and focuses first missing field", () => {
    const params = buildParams();
    const manager = createShoppingManager(params);

    manager.addLink();

    expect(params.itemInput.focus).toHaveBeenCalled();
    expect(document.querySelectorAll(".client-required-error").length).toBe(3);
  });

  test("adds link, normalizes url, renders list, and remove works", () => {
    const file = { name: "pic.png" };
    const params = buildParams({
      getFiles: jest.fn(() => [file])
    });
    params.itemInput.value = "Milk";
    params.linkInput.value = "shop.com";
    const manager = createShoppingManager(params);

    manager.addLink();

    expect(params.w.URL.createObjectURL).toHaveBeenCalledWith(file);
    expect(params.setInputFiles).toHaveBeenCalledWith(params.shopImageInput, expect.any(Array));
    expect(params.shoppingField.value).toContain("Milk | https://shop.com");
    expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(1);

    params.listBox.querySelector(".remove").click();
    expect(params.listBox.textContent).toContain("No shopping links added yet.");
    expect(params.shoppingField.value).toBe("");
  });

  test("bind handles Enter key submission and clears errors on input", () => {
    const params = buildParams({
      getFiles: jest.fn(() => [{ name: "x.png" }])
    });
    const manager = createShoppingManager(params);
    manager.bind();

    params.itemInput.value = "Eggs";
    params.linkInput.value = "eggs.com";
    params.shopImageInput.dispatchEvent(new Event("change"));
    const event = new KeyboardEvent("keydown", { key: "Enter" });
    params.linkInput.dispatchEvent(event);

    expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(1);

    // Add an error then clear it through input event
    params.itemInput.value = "";
    manager.addLink();
    expect(params.itemWrapper.querySelector(".client-required-error")).not.toBeNull();
    params.itemInput.dispatchEvent(new Event("input"));
    expect(params.itemWrapper.querySelector(".client-required-error")).toBeNull();
  });

  test("shop image change renders preview and remove clears pending", () => {
    const params = buildParams({
      getFiles: jest.fn(() => [{ name: "preview.png" }])
    });
    const manager = createShoppingManager(params);
    manager.bind();

    params.shopImageInput.dispatchEvent(new Event("change"));
    expect(params.shopImageList.querySelector(".image-preview-item")).not.toBeNull();
    params.shopImageList.querySelector(".image-remove").click();
    expect(params.shopImageList.innerHTML).toBe("");
  });

  test("limits shopping links to 10 and clears limit error after removal", () => {
    const params = buildParams({
      getFiles: jest.fn(() => [{ name: "pic.png" }])
    });
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
    expect(params.listBox.querySelectorAll(".shopping-list-item").length).toBe(10);
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
});
