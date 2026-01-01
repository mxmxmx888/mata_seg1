const { initCreateRecipe } = require("../../static/js/create_recipe");
const { buildForm, flushPromises, mockFiles, registerDomHooks } = require("./support/createRecipeTestUtils");

registerDomHooks();

const setReader = (impl) => {
  const original = window.FileReader;
  window.FileReader = jest.fn(() => impl);
  return () => {
    window.FileReader = original;
  };
};

afterEach(() => {
  jest.clearAllMocks();
  sessionStorage.clear();
});

test("persists selected image files to sessionStorage on change", async () => {
  buildForm({ bound: true });
  const imageInput = document.getElementById("id_images");
  mockFiles(imageInput, [new File(["abc"], "photo.png", { type: "image/png", lastModified: 123 })]);
  const restoreReader = setReader({
    readAsDataURL() {
      this.result = "data:image/png;base64,AAA";
      if (this.onload) this.onload();
    }
  });
  initCreateRecipe(window);
  imageInput.dispatchEvent(new Event("change"));
  await flushPromises();
  expect(sessionStorage.getItem("create-recipe-images")).toContain("photo.png");
  restoreReader();
});

test("restores files from sessionStorage when bound with errors", async () => {
  buildForm({ bound: true, hasErrors: true });
  const stored = [{ name: "saved.png", type: "image/png", lastModified: 123, data: "data:image/png;base64,ABC" }];
  sessionStorage.setItem("create-recipe-images", JSON.stringify(stored));
  global.fetch = jest.fn().mockResolvedValue({ blob: () => Promise.resolve(new Blob(["data"], { type: "image/png" })) });
  initCreateRecipe(window);
  await flushPromises();
  expect(document.getElementById("image-file-list").textContent).toContain("saved.png");
});

test("keeps existing images when change event has no new files", async () => {
  buildForm({ bound: true });
  const imageInput = document.getElementById("id_images");
  mockFiles(imageInput, [new File(["abc"], "keep.png", { type: "image/png" })]);
  initCreateRecipe(window);
  imageInput.dispatchEvent(new Event("change"));
  mockFiles(imageInput, []);
  imageInput.dispatchEvent(new Event("change"));
  await flushPromises();
  expect(document.getElementById("image-file-list").textContent).toContain("keep.png");
});

test("appends new images instead of replacing existing ones", async () => {
  buildForm({ bound: true });
  const input = document.getElementById("id_images");
  mockFiles(input, [new File(["a"], "first.png", { type: "image/png" })]);
  initCreateRecipe(window);
  input.dispatchEvent(new Event("change"));
  mockFiles(input, [new File(["b"], "second.png", { type: "image/png" })]);
  input.dispatchEvent(new Event("change"));
  await flushPromises();
  const text = document.getElementById("image-file-list").textContent;
  expect(text).toContain("first.png");
  expect(text).toContain("second.png");
});

test("removes a single image when remove button clicked", async () => {
  buildForm({ bound: true });
  const input = document.getElementById("id_images");
  mockFiles(input, [new File(["a"], "first.png", { type: "image/png" }), new File(["b"], "second.png", { type: "image/png" })]);
  initCreateRecipe(window);
  input.dispatchEvent(new Event("change"));
  document.querySelector(".image-remove").click();
  await flushPromises();
  const text = document.getElementById("image-file-list").textContent;
  expect(text).not.toContain("first.png");
  expect(text).toContain("second.png");
});

test("handles FileReader errors by clearing persisted data", async () => {
  buildForm({ bound: true });
  const input = document.getElementById("id_images");
  mockFiles(input, [new File(["abc"], "bad.png", { type: "image/png" })]);
  const restoreReader = setReader({
    readAsDataURL() {
      if (this.onerror) this.onerror(new Error("boom"));
    }
  });
  sessionStorage.setItem("create-recipe-images", "keep");
  initCreateRecipe(window);
  input.dispatchEvent(new Event("change"));
  await flushPromises();
  expect(sessionStorage.getItem("create-recipe-images")).toBeNull();
  restoreReader();
});

test("ignores bad stored JSON gracefully", () => {
  buildForm({ bound: true, hasErrors: true });
  sessionStorage.setItem("create-recipe-images", "{bad json");
  initCreateRecipe(window);
  expect(document.getElementById("image-file-list").textContent).toBe("");
});

test("continues restore loop on fetch error", async () => {
  buildForm({ bound: true, hasErrors: true });
  sessionStorage.setItem(
    "create-recipe-images",
    JSON.stringify([
      { name: "good.png", data: "data:image/png;base64,ABC" },
      { name: "bad.png", data: "data:image/png;base64,DEF" }
    ])
  );
  global.fetch = jest
    .fn()
    .mockRejectedValueOnce(new Error("fail"))
    .mockResolvedValueOnce({ blob: () => Promise.resolve(new Blob(["x"], { type: "image/png" })) });
  initCreateRecipe(window);
  await flushPromises();
  expect(document.getElementById("image-file-list").textContent).toContain("bad.png");
});

test("restores files even when DataTransfer unavailable", async () => {
  const realDT = window.DataTransfer;
  const realFetch = global.fetch;
  delete window.DataTransfer;
  global.fetch = jest.fn().mockResolvedValue({ blob: () => Promise.resolve(new Blob(["x"], { type: "image/png" })) });
  buildForm({ bound: true, hasErrors: true });
  sessionStorage.setItem("create-recipe-images", JSON.stringify([{ name: "x.png", data: "data:image/png;base64,AAA" }]));
  initCreateRecipe(window);
  await flushPromises();
  expect(document.getElementById("image-file-list").textContent).toContain("x.png");
  window.DataTransfer = realDT;
  global.fetch = realFetch;
});

test("renderRequiredFieldErrors handles file validity with mock files", () => {
  buildForm();
  const input = document.getElementById("id_images");
  mockFiles(input, [new File(["x"], "x.png")]);
  initCreateRecipe(window);
  expect(document.querySelectorAll(".client-required-error").length).toBe(0);
});

test("persistFiles handles empty files array and storage errors gracefully", async () => {
  buildForm();
  const input = document.getElementById("id_images");
  mockFiles(input, []);
  const removeSpy = jest.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
    throw new Error("fail");
  });
  initCreateRecipe(window);
  input.dispatchEvent(new Event("change"));
  await flushPromises();
  removeSpy.mockRestore();
});
