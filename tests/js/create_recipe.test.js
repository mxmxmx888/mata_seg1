const { initCreateRecipe, normalizeUrl } = require("../../static/js/create_recipe");

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

describe("create_recipe", () => {
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

  test("normalizeUrl prefixes https when missing", () => {
    expect(normalizeUrl("example.com")).toBe("https://example.com");
    expect(normalizeUrl("http://example.com")).toBe("http://example.com");
    expect(normalizeUrl("")).toBe("");
  });

  test("adds a shopping link and syncs fields", () => {
    buildForm();
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    const shopImageInput = document.getElementById("id_shop_images");
    Object.defineProperty(shopImageInput, "files", { value: [file], configurable: true });

    document.getElementById("shop-item").value = "Banana";
    document.getElementById("shop-link").value = "banana.com";

    initCreateRecipe(window);

    document.getElementById("add-shop-link").click();

    const listBox = document.getElementById("shop-list");
    expect(listBox.querySelectorAll(".shopping-list-item").length).toBe(1);
    expect(document.getElementById("id_shopping_links_text").value).toContain("Banana | https://banana.com");
    expect(document.getElementById("shop-image-file-list").textContent).toContain("pic.jpg");
  });

  test("shows validation errors when fields missing", () => {
    buildForm();
    initCreateRecipe(window);
    document.getElementById("add-shop-link").click();
    expect(document.querySelectorAll(".client-required-error").length).toBe(3);
  });

  test("removes shopping link", () => {
    buildForm();
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    const shopImageInput = document.getElementById("id_shop_images");
    Object.defineProperty(shopImageInput, "files", { value: [file], configurable: true });
    document.getElementById("shop-item").value = "Banana";
    document.getElementById("shop-link").value = "banana.com";

    initCreateRecipe(window);
    document.getElementById("add-shop-link").click();

    const removeBtn = document.querySelector(".remove");
    removeBtn.click();

    expect(document.getElementById("shop-list").textContent).toMatch(/No shopping links/i);
    expect(document.getElementById("id_shopping_links_text").value).toBe("");
  });

  test("bootstraps existing shopping field entries", () => {
    buildForm();
    const shoppingField = document.getElementById("id_shopping_links_text");
    shoppingField.value = "Apple | apple.com\nOrange";
    initCreateRecipe(window);
    expect(document.querySelectorAll(".shopping-list-item").length).toBe(2);
    expect(document.getElementById("id_shopping_links_text").value).toContain("https://apple.com");
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

  test("persists selected image files to sessionStorage on change", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "photo.png", { type: "image/png", lastModified: 123 });
    Object.defineProperty(imageInput, "files", { value: [file], configurable: true });

    class MockReader {
      readAsDataURL(f) {
        this.result = "data:image/png;base64,AAA";
        if (this.onload) this.onload();
      }
    }
    const originalReader = window.FileReader;
    window.FileReader = jest.fn(() => new MockReader());

    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(sessionStorage.getItem("create-recipe-images")).toContain("photo.png");
    window.FileReader = originalReader;
  });

  test("restores files from sessionStorage when bound with errors", async () => {
    buildForm({ bound: true, hasErrors: true });
    const imageInput = document.getElementById("id_images");
    const imageList = document.getElementById("image-file-list");
    const stored = [
      {
        name: "saved.png",
        type: "image/png",
        lastModified: 123,
        data: "data:image/png;base64,ABC"
      }
    ];
    sessionStorage.setItem("create-recipe-images", JSON.stringify(stored));

    const mockBlob = new Blob(["data"], { type: "image/png" });
    global.fetch = jest.fn().mockResolvedValue({
      blob: () => Promise.resolve(mockBlob)
    });

    initCreateRecipe(window);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(imageList.textContent).toContain("saved.png");
  });

  test("clears image list when change event has no files and removes persisted entry", () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const removeSpy = jest.spyOn(Storage.prototype, "removeItem");

    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));

    expect(document.getElementById("image-file-list").textContent).toBe("");
    expect(removeSpy).toHaveBeenCalledWith("create-recipe-images");
    removeSpy.mockRestore();
  });

  test("focuses missing url then missing image", () => {
    buildForm();
    const shopImageInput = document.getElementById("id_shop_images");
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    Object.defineProperty(shopImageInput, "files", { value: [file], configurable: true });

    initCreateRecipe(window);
    document.getElementById("shop-item").value = "Item";
    document.getElementById("add-shop-link").click();
    expect(document.activeElement).toBe(document.getElementById("shop-link"));

    document.getElementById("shop-link").value = "https://ok.com";
    Object.defineProperty(shopImageInput, "files", { value: [], configurable: true });
    document.getElementById("add-shop-link").click();
    expect(document.activeElement).toBe(shopImageInput);
  });

  test("submit succeeds when required fields filled and trims ingredients", () => {
    buildForm();
    const form = document.querySelector("form");
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "photo.png", { type: "image/png" });
    Object.defineProperty(imageInput, "files", { value: [file], configurable: true });
    document.getElementById("title").value = "Title";
    document.getElementById("id_ingredients_text").value = " apple \n banana ";

    initCreateRecipe(window);
    const result = form.dispatchEvent(new Event("submit", { cancelable: true }));

    expect(result).toBe(true);
    expect(document.getElementById("id_ingredients_text").value).toBe("apple\nbanana");
  });

  test("handles FileReader errors by clearing persisted data", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "bad.png", { type: "image/png" });
    Object.defineProperty(imageInput, "files", { value: [file], configurable: true });

    class ErrorReader {
      readAsDataURL() {
        if (this.onerror) this.onerror(new Error("boom"));
      }
    }
    const originalReader = window.FileReader;
    window.FileReader = jest.fn(() => new ErrorReader());
    sessionStorage.setItem("create-recipe-images", "keep");

    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(sessionStorage.getItem("create-recipe-images")).toBeNull();
    window.FileReader = originalReader;
  });

  test("ignores bad stored JSON gracefully", () => {
    buildForm({ bound: true, hasErrors: true });
    sessionStorage.setItem("create-recipe-images", "{bad json");
    initCreateRecipe(window);
    expect(document.getElementById("image-file-list").textContent).toBe("");
  });

  test("continues restore loop on fetch error", async () => {
    buildForm({ bound: true, hasErrors: true });
    const stored = [
      { name: "good.png", data: "data:image/png;base64,ABC" },
      { name: "bad.png", data: "data:image/png;base64,DEF" }
    ];
    sessionStorage.setItem("create-recipe-images", JSON.stringify(stored));

    global.fetch = jest
      .fn()
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce({
        blob: () => Promise.resolve(new Blob(["x"], { type: "image/png" }))
      });

    initCreateRecipe(window);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.getElementById("image-file-list").textContent).toContain("bad.png");
  });

  test("enter key triggers addLink for item and link inputs", () => {
    buildForm();
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    const shopImageInput = document.getElementById("id_shop_images");
    Object.defineProperty(shopImageInput, "files", { value: [file], configurable: true });
    document.getElementById("shop-item").value = "Kiwi";
    document.getElementById("shop-link").value = "kiwi.com";

    initCreateRecipe(window);

    const itemInput = document.getElementById("shop-item");
    itemInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    const linkInput = document.getElementById("shop-link");
    linkInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    expect(document.querySelectorAll(".shopping-list-item").length).toBeGreaterThan(0);
  });

});
