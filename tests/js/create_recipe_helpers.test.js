const { getFiles } = require("../../static/js/create_recipe_helpers");

function loadHelpersWithOverrides(overrides = {}) {
  jest.resetModules();
  const imagesPath = "../../static/js/create_recipe_images";
  const validationPath = "../../static/js/create_recipe_validation";
  const shoppingPath = "../../static/js/create_recipe_shopping";
  if (overrides.images) {
    jest.doMock(imagesPath, () => overrides.images);
  }
  if (overrides.validation) {
    jest.doMock(validationPath, () => overrides.validation);
  }
  if (overrides.shopping) {
    jest.doMock(shoppingPath, () => overrides.shopping);
  }
  let helpers;
  jest.isolateModules(() => {
    helpers = require("../../static/js/create_recipe_helpers");
  });
  return helpers;
}

describe("create_recipe_helpers utilities", () => {
  afterEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  test("loadHelpersWithOverrides replaces dependent modules", () => {
    const clear = jest.fn();
    const imageManager = jest.fn();
    const shoppingManager = jest.fn();
    const validator = jest.fn();
    const helpers = loadHelpersWithOverrides({
      images: { clearStoredFiles: clear, createImageManager: imageManager },
      shopping: { createShoppingManager: shoppingManager },
      validation: { createRequiredFieldValidator: validator }
    });
    expect(helpers.clearStoredFiles).toBe(clear);
    expect(helpers.createImageManager).toBe(imageManager);
    expect(helpers.createShoppingManager).toBe(shoppingManager);
    expect(helpers.createRequiredFieldValidator).toBe(validator);
  });

  test("normalizeUrl handles blank, prefixed, and unprefixed urls", () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    expect(helpers.normalizeUrl("")).toBe("");
    expect(helpers.normalizeUrl("https://example.com")).toBe("https://example.com");
    expect(helpers.normalizeUrl("example.com")).toBe("https://example.com");
  });

  test("getFiles prefers real files then falls back to mock files", () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const input = { files: [{ name: "real" }] };
    expect(helpers.getFiles(input)[0].name).toBe("real");
    const mockInput = { files: [], __mockFiles: ["mock"] };
    expect(helpers.getFiles(mockInput)).toEqual(["mock"]);
    expect(helpers.getFiles(null)).toBeNull();
  });

  test("persistFiles stores file metadata and clears when empty", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const stored = {};
    const win = {
      sessionStorage: {
        setItem: jest.fn((k, v) => {
          stored[k] = v;
        }),
        removeItem: jest.fn((k) => delete stored[k])
      },
      FileReader: class {
        readAsDataURL(file) {
          this.result = `data:${file.name}`;
          if (this.onload) this.onload();
        }
      }
    };
    const files = [{ name: "one.png", type: "image/png", lastModified: 5 }];
    const input = { files };

    helpers.persistFiles(win, input, "key");
    await new Promise((r) => setTimeout(r, 0));
    expect(win.sessionStorage.setItem).toHaveBeenCalledWith("key", expect.any(String));
    const parsed = JSON.parse(stored.key);
    expect(parsed[0].name).toBe("one.png");

    helpers.persistFiles(win, { files: [] }, "key");
    expect(win.sessionStorage.removeItem).toHaveBeenCalledWith("key");
  });

  test("persistFiles removes storage when FileReader fails", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const win = {
      sessionStorage: {
        setItem: jest.fn(),
        removeItem: jest.fn()
      },
      FileReader: class {
        readAsDataURL() {
          if (this.onerror) this.onerror(new Error("boom"));
        }
      }
    };
    const files = [{ name: "bad.png", type: "image/png", lastModified: 2 }];

    helpers.persistFiles(win, { files }, "bad");
    await new Promise((r) => setTimeout(r, 0));

    expect(win.sessionStorage.removeItem).toHaveBeenCalledWith("bad");
  });

  test("restoreFiles reconstructs FileList via DataTransfer", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const onAfterRestore = jest.fn();
    const filesAdded = [];
    const stubBlob = { type: "text/plain" };
    const win = {
      DataTransfer: class {
        constructor() {
          this.items = { add: (file) => filesAdded.push(file) };
          this.files = filesAdded;
        }
      },
      File: class {
        constructor(parts, name, opts = {}) {
          this.parts = parts;
          this.name = name;
          this.type = opts.type || "";
          this.lastModified = opts.lastModified || 0;
        }
      },
      fetch: () => Promise.resolve({ blob: () => Promise.resolve(stubBlob) }),
      sessionStorage: {
        getItem: () =>
          JSON.stringify([
            {
              name: "restored.txt",
              type: "text/plain",
              lastModified: 123,
              data: "data:text/plain;base64,aGVsbG8="
            }
          ])
      }
    };
    const input = {};

    await helpers.restoreFiles(win, input, "key", onAfterRestore);

    expect(filesAdded.length).toBe(1);
    expect(input.__mockFiles).toEqual(filesAdded);
    expect(onAfterRestore).toHaveBeenCalled();
  });

  test("restoreFiles uses defaults when metadata missing", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const created = [];
    const win = {
      DataTransfer: class {
        constructor() {
          this.items = { add: (file) => created.push(file) };
          this.files = created;
        }
      },
      File: class {
        constructor(parts, name, opts = {}) {
          this.parts = parts;
          this.name = name;
          this.type = opts.type || "";
          this.lastModified = opts.lastModified || 0;
        }
      },
      fetch: () => Promise.resolve({ blob: () => Promise.resolve({ type: "" }) }),
      sessionStorage: { getItem: () => JSON.stringify([{ data: "data:;base64,aGVsbG8=" }]) }
    };
    const input = {};

    await helpers.restoreFiles(win, input, "key");

    expect(created.length).toBe(1);
    expect(created[0].name).toBe("upload");
    expect(created[0].type).toBe("application/octet-stream");
    expect(typeof created[0].lastModified).toBe("number");
  });

  test("restoreFiles skips when fetch fails", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const win = {
      File: class {
        constructor(parts, name, opts = {}) {
          this.parts = parts;
          this.name = name;
          this.type = opts.type || "";
          this.lastModified = opts.lastModified || 0;
        }
      },
      fetch: () => Promise.reject(new Error("fail")),
      sessionStorage: { getItem: () => JSON.stringify([{ data: "data:text/plain;base64,aGVsbG8=" }]) }
    };
    const input = {};

    await helpers.restoreFiles(win, input, "key");

    expect(input.__mockFiles).toBeUndefined();
  });

  test("restoreFiles falls back when DataTransfer unavailable", async () => {
    const helpers = require("../../static/js/create_recipe_helpers");
    const stubBlob = { type: "text/plain" };
    const win = {
      File: class {
        constructor(parts, name, opts = {}) {
          this.parts = parts;
          this.name = name;
          this.type = opts.type || "";
          this.lastModified = opts.lastModified || 0;
        }
      },
      fetch: () => Promise.resolve({ blob: () => Promise.resolve(stubBlob) }),
      sessionStorage: {
        getItem: () =>
          JSON.stringify([
            { name: "restored.txt", type: "text/plain", lastModified: 123, data: "data:text/plain;base64,aGVsbG8=" }
          ])
      }
    };
    const input = {};

    await helpers.restoreFiles(win, input, "key");

    expect(Array.isArray(input.__mockFiles)).toBe(true);
    expect(input.__mockFiles.length).toBe(1);
  });

  test("createRequiredFieldValidator fallback renders and clears errors", () => {
    const helpers = loadHelpersWithOverrides({ validation: {} });
    const realValidation = jest.requireActual("../../static/js/create_recipe_validation");
    expect(helpers.createRequiredFieldValidator).not.toBe(realValidation.createRequiredFieldValidator);
    const form = document.createElement("form");

    const containerWithFeedback = document.createElement("div");
    containerWithFeedback.className = "mb-3";
    const fieldWithFeedback = document.createElement("input");
    fieldWithFeedback.required = true;
    const invalidFeedback = document.createElement("div");
    invalidFeedback.className = "invalid-feedback";
    containerWithFeedback.appendChild(invalidFeedback);
    containerWithFeedback.appendChild(fieldWithFeedback);

    const containerNoFeedback = document.createElement("div");
    const fieldWithoutFeedback = document.createElement("input");
    fieldWithoutFeedback.required = true;
    containerNoFeedback.appendChild(fieldWithoutFeedback);

    const fileContainer = document.createElement("div");
    const fileField = document.createElement("input");
    fileField.type = "file";
    fileField.required = true;
    fileContainer.appendChild(fileField);

    form.appendChild(containerWithFeedback);
    form.appendChild(containerNoFeedback);
    form.appendChild(fileContainer);

    const validator = helpers.createRequiredFieldValidator(
      document,
      form,
      [fieldWithFeedback, fieldWithoutFeedback, fileField],
      () => ["file"]
    );

    const hasErrors = validator.renderRequiredFieldErrors();
    expect(hasErrors).toBe(true);
    expect(containerWithFeedback.querySelector(".client-required-error")).not.toBeNull();
    expect(containerNoFeedback.querySelector(".client-required-error")).not.toBeNull();
    expect(fileContainer.querySelector(".client-required-error")).toBeNull();

    fieldWithFeedback.value = "ok";
    validator.bindRequiredListeners();
    fieldWithFeedback.dispatchEvent(new Event("input"));
    expect(containerWithFeedback.querySelector(".client-required-error")).toBeNull();
  });

  test("createRequiredFieldValidator handles missing helpers and events", () => {
    const helpers = loadHelpersWithOverrides({ validation: {} });
    const form = document.createElement("form");
    const loneField = {
      type: "text",
      value: "",
      validity: { valueMissing: true },
      closest: () => null,
      parentElement: form,
      addEventListener: jest.fn(),
      insertAdjacentElement: jest.fn()
    };

    const validator = helpers.createRequiredFieldValidator(document, form, [loneField]);
    expect(validator.renderRequiredFieldErrors()).toBe(true);
    expect(form.querySelector(".client-required-error")).not.toBeNull();

    validator.bindRequiredListeners();
    const changeHandler = loneField.addEventListener.mock.calls.find((call) => call[0] === "change")[1];
    changeHandler();
    expect(form.querySelector(".client-required-error")).toBeNull();
  });

  test("clearStoredFiles and fallback managers no-op safely", () => {
    const helpers = loadHelpersWithOverrides({ images: {}, shopping: {} });
    const realImages = jest.requireActual("../../static/js/create_recipe_images");
    const realShopping = jest.requireActual("../../static/js/create_recipe_shopping");
    expect(helpers.clearStoredFiles).not.toBe(realImages.clearStoredFiles);
    expect(helpers.createImageManager).not.toBe(realImages.createImageManager);
    expect(helpers.createShoppingManager).not.toBe(realShopping.createShoppingManager);
    const win = {
      sessionStorage: { removeItem: jest.fn() }
    };
    helpers.clearStoredFiles(win, "foo");
    expect(win.sessionStorage.removeItem).toHaveBeenCalledWith("foo");

    const imageManager = helpers.createImageManager();
    expect(() => {
      imageManager.bind();
      imageManager.renderImagesList();
      imageManager.hydrateImagesFromInput();
      imageManager.removeImageAt();
      imageManager.syncImageFiles();
      imageManager.restoreFromStorage();
      imageManager.persistSelection();
    }).not.toThrow();

    const shoppingManager = helpers.createShoppingManager();
    expect(() => {
      shoppingManager.addLink();
      shoppingManager.bind();
      shoppingManager.bootstrapExisting();
      shoppingManager.renderList();
      shoppingManager.syncShoppingField();
      shoppingManager.syncShopImagesInput();
    }).not.toThrow();
  });
});
