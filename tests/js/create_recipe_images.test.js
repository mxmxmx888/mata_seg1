const { initCreateRecipe } = require("../../static/js/create_recipe");
const { buildForm, flushPromises, mockFiles, registerDomHooks } = require("./support/createRecipeTestUtils");

describe("create_recipe images", () => {
  registerDomHooks();

  test("persists selected image files to sessionStorage on change", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "photo.png", { type: "image/png", lastModified: 123 });
    mockFiles(imageInput, [file]);

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
    await flushPromises();
    await flushPromises();

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
    await flushPromises();
    await flushPromises();

    expect(imageList.textContent).toContain("saved.png");
  });

  test("keeps existing images when change event has no new files", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "keep.png", { type: "image/png" });
    mockFiles(imageInput, [file]);

    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change")); // initial hydrate
    mockFiles(imageInput, []);
    imageInput.dispatchEvent(new Event("change")); // user cancels dialog
    await flushPromises();

    expect(document.getElementById("image-file-list").textContent).toContain("keep.png");
  });

  test("appends new images instead of replacing existing ones", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const first = new File(["a"], "first.png", { type: "image/png" });
    mockFiles(imageInput, [first]);
    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));

    const second = new File(["b"], "second.png", { type: "image/png" });
    mockFiles(imageInput, [second]);
    imageInput.dispatchEvent(new Event("change"));
    await flushPromises();

    const text = document.getElementById("image-file-list").textContent;
    expect(text).toContain("first.png");
    expect(text).toContain("second.png");
  });

  test("removes a single image when X button clicked", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const first = new File(["a"], "first.png", { type: "image/png" });
    const second = new File(["b"], "second.png", { type: "image/png" });
    mockFiles(imageInput, [first, second]);
    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));

    const removeBtn = document.querySelector(".image-remove");
    removeBtn.click();
    await flushPromises();

    const text = document.getElementById("image-file-list").textContent;
    expect(text).not.toContain("first.png");
    expect(text).toContain("second.png");
  });

  test("handles FileReader errors by clearing persisted data", async () => {
    buildForm({ bound: true });
    const imageInput = document.getElementById("id_images");
    const file = new File(["abc"], "bad.png", { type: "image/png" });
    mockFiles(imageInput, [file]);

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
    await flushPromises();

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
    await flushPromises();

    expect(document.getElementById("image-file-list").textContent).toContain("bad.png");
  });

  test("restores files even when DataTransfer unavailable", async () => {
    const realDT = window.DataTransfer;
    const realFetch = global.fetch;
    delete window.DataTransfer;
    global.fetch = jest.fn().mockResolvedValue({
      blob: () => Promise.resolve(new Blob(["x"], { type: "image/png" }))
    });
    buildForm({ bound: true, hasErrors: true });
    sessionStorage.setItem(
      "create-recipe-images",
      JSON.stringify([{ name: "x.png", data: "data:image/png;base64,AAA" }])
    );
    initCreateRecipe(window);
    await flushPromises();
    await flushPromises();
    expect(document.getElementById("image-file-list").textContent).toContain("x.png");
    window.DataTransfer = realDT;
    global.fetch = realFetch;
  });

  test("renderRequiredFieldErrors handles file validity with mock files", () => {
    buildForm();
    const imageInput = document.getElementById("id_images");
    mockFiles(imageInput, [new File(["x"], "x.png")]);
    initCreateRecipe(window);
    expect(document.querySelectorAll(".client-required-error").length).toBe(0);
  });

  test("persistFiles handles empty files array and storage errors gracefully", async () => {
    buildForm();
    const imageInput = document.getElementById("id_images");
    mockFiles(imageInput, []);
    const removeSpy = jest.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("fail");
    });
    initCreateRecipe(window);
    imageInput.dispatchEvent(new Event("change"));
    await flushPromises();
    removeSpy.mockRestore();
  });
});
