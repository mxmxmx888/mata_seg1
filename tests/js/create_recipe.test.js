const { initCreateRecipe, normalizeUrl } = require("../../static/js/create_recipe");
const { buildForm, mockFiles, registerDomHooks } = require("./support/createRecipeTestUtils");

describe("create_recipe", () => {
  registerDomHooks();

  test("normalizeUrl prefixes https when missing", () => {
    expect(normalizeUrl("example.com")).toBe("https://example.com");
    expect(normalizeUrl("http://example.com")).toBe("http://example.com");
    expect(normalizeUrl("")).toBe("");
  });

  test("adds a shopping link and syncs fields", () => {
    buildForm();
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    const shopImageInput = document.getElementById("id_shop_images");
    mockFiles(shopImageInput, [file]);

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
    mockFiles(shopImageInput, [file]);
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

  test("focuses missing url then missing image", () => {
    buildForm();
    const shopImageInput = document.getElementById("id_shop_images");
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    mockFiles(shopImageInput, [file]);

    initCreateRecipe(window);
    document.getElementById("shop-item").value = "Item";
    document.getElementById("add-shop-link").click();
    expect(document.activeElement).toBe(document.getElementById("shop-link"));

    document.getElementById("shop-link").value = "https://ok.com";
    mockFiles(shopImageInput, []);
    document.getElementById("add-shop-link").click();
    expect(document.activeElement).toBe(shopImageInput);
  });

  test("submit succeeds when required fields filled and trims ingredients", () => {
    buildForm();
    const form = document.querySelector("form");
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "photo.png", { type: "image/png" });
    mockFiles(imageInput, [file]);
    document.getElementById("title").value = "Title";
    document.getElementById("id_ingredients_text").value = " apple \n banana ";

    initCreateRecipe(window);
    const result = form.dispatchEvent(new Event("submit", { cancelable: true }));

    expect(result).toBe(true);
    expect(document.getElementById("id_ingredients_text").value).toBe("apple\nbanana");
  });

  test("enter key triggers addLink for item and link inputs", () => {
    buildForm();
    const file = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    const shopImageInput = document.getElementById("id_shop_images");
    mockFiles(shopImageInput, [file]);
    document.getElementById("shop-item").value = "Kiwi";
    document.getElementById("shop-link").value = "kiwi.com";

    initCreateRecipe(window);

    const itemInput = document.getElementById("shop-item");
    itemInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    const linkInput = document.getElementById("shop-link");
    linkInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

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
    if (readyDescriptor) {
      Object.defineProperty(document, "readyState", readyDescriptor);
    }
  });

  test("bootstrapExisting handles lines without names and normalizes urls", () => {
    buildForm();
    const field = document.getElementById("id_shopping_links_text");
    field.value = " | example.com\nItem | http://ok.com";
    initCreateRecipe(window);
    expect(document.querySelectorAll(".shopping-list-item").length).toBe(1);
    expect(field.value).toContain("http://ok.com");
  });
});
