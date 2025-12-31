const helpersPath = "../../static/js/create_recipe_helpers";
const { getFiles } = require(helpersPath);

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

const requireHelpers = () => require(helpersPath);

const makeFileCtor = (defaultType = "", defaultLastModified = 0) =>
  class {
    constructor(parts, name, opts = {}) {
      this.parts = parts;
      this.name = name;
      this.type = opts.type || defaultType;
      this.lastModified = opts.lastModified ?? defaultLastModified;
    }
  };

const makeDataTransfer = (bucket = []) =>
  class {
    constructor() {
      this.items = { add: (file) => bucket.push(file) };
      this.files = bucket;
    }
  };

function makePersistWin({ fail } = {}) {
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
        if (fail && this.onerror) {
          this.onerror(new Error("boom"));
          return;
        }
        this.result = `data:${file.name}`;
        if (this.onload) this.onload();
      }
    }
  };
  return { win, stored };
}

describe("create_recipe_helpers utilities", () => {
  afterEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  describe("module loading", () => {
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
      const helpers = requireHelpers();
      expect(helpers.normalizeUrl("")).toBe("");
      expect(helpers.normalizeUrl("https://example.com")).toBe("https://example.com");
      expect(helpers.normalizeUrl("example.com")).toBe("https://example.com");
    });

    test("getFiles prefers real files then falls back to mock files", () => {
      const helpers = requireHelpers();
      const input = { files: [{ name: "real" }] };
      expect(helpers.getFiles(input)[0].name).toBe("real");
      const mockInput = { files: [], __mockFiles: ["mock"] };
      expect(helpers.getFiles(mockInput)).toEqual(["mock"]);
      expect(helpers.getFiles(null)).toBeNull();
    });
  });

  describe("persistFiles", () => {
    test("stores file metadata and clears when empty", async () => {
      const helpers = requireHelpers();
      const { win, stored } = makePersistWin();
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

    test("removes storage when FileReader fails", async () => {
      const helpers = requireHelpers();
      const { win } = makePersistWin({ fail: true });
      const files = [{ name: "bad.png", type: "image/png", lastModified: 2 }];

      helpers.persistFiles(win, { files }, "bad");
      await new Promise((r) => setTimeout(r, 0));

      expect(win.sessionStorage.removeItem).toHaveBeenCalledWith("bad");
    });
  });

  describe("restoreFiles", () => {
    test("reconstructs FileList via DataTransfer", async () => {
      const helpers = requireHelpers();
      const onAfterRestore = jest.fn();
      const filesAdded = [];
      const stubBlob = { type: "text/plain" };
      const win = {
        DataTransfer: makeDataTransfer(filesAdded),
        File: makeFileCtor(),
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

    test("uses defaults when metadata missing", async () => {
      const helpers = requireHelpers();
      const created = [];
      const win = {
        DataTransfer: makeDataTransfer(created),
        File: makeFileCtor(),
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

    test("skips when fetch fails", async () => {
      const helpers = requireHelpers();
      const win = {
        File: makeFileCtor(),
        fetch: () => Promise.reject(new Error("fail")),
        sessionStorage: { getItem: () => JSON.stringify([{ data: "data:text/plain;base64,aGVsbG8=" }]) }
      };
      const input = {};

      await helpers.restoreFiles(win, input, "key");

      expect(input.__mockFiles).toBeUndefined();
    });

    test("falls back when DataTransfer unavailable", async () => {
      const helpers = requireHelpers();
      const stubBlob = { type: "text/plain" };
      const win = {
        File: makeFileCtor(),
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
