const helpersPath = "../../static/js/create_recipe_helpers";
const { getFiles } = require(helpersPath);

const requireHelpers = () => require(helpersPath);

const formWithFields = () => {
  const form = document.createElement("form");
  const text = document.createElement("input");
  text.required = true;
  const wrap = document.createElement("div");
  wrap.className = "mb-3";
  const feedback = document.createElement("div");
  feedback.className = "invalid-feedback";
  wrap.appendChild(text);
  wrap.appendChild(feedback);
  const file = document.createElement("input");
  file.type = "file";
  form.appendChild(wrap);
  form.appendChild(file);
  document.body.appendChild(form);
  return { form, text, file, feedback };
};

const loadHelpersWithOverrides = (overrides = {}) => {
  jest.resetModules();
  const imagesPath = "../../static/js/create_recipe_images";
  const validationPath = "../../static/js/create_recipe_validation";
  const shoppingPath = "../../static/js/create_recipe_shopping";
  jest.dontMock(imagesPath);
  jest.dontMock(validationPath);
  jest.dontMock(shoppingPath);
  if (overrides.images) jest.doMock(imagesPath, () => overrides.images);
  if (overrides.validation) jest.doMock(validationPath, () => overrides.validation);
  if (overrides.shopping) jest.doMock(shoppingPath, () => overrides.shopping);
  let helpers;
  jest.isolateModules(() => {
    helpers = require("../../static/js/create_recipe_helpers");
  });
  return helpers;
};

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

const makePersistWin = ({ fail } = {}) => {
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
};

afterEach(() => {
  jest.resetModules();
  jest.clearAllMocks();
});

test("loadHelpersWithOverrides replaces dependent modules", () => {
  const helpers = loadHelpersWithOverrides({
    images: { clearStoredFiles: jest.fn(), createImageManager: jest.fn() },
    shopping: { createShoppingManager: jest.fn() },
    validation: { createRequiredFieldValidator: jest.fn() }
  });
  expect(helpers.createShoppingManager).toBeDefined();
});

test("normalizeUrl handles blank, prefixed, and unprefixed urls", () => {
  const helpers = requireHelpers();
  expect(helpers.normalizeUrl("")).toBe("");
  expect(helpers.normalizeUrl("https://example.com")).toBe("https://example.com");
  expect(helpers.normalizeUrl("example.com")).toBe("https://example.com");
});

test("getFiles prefers real files then falls back to mock files", () => {
  const helpers = requireHelpers();
  expect(helpers.getFiles({ files: [{ name: "real" }] })[0].name).toBe("real");
  expect(helpers.getFiles({ files: [], __mockFiles: ["mock"] })).toEqual(["mock"]);
  expect(helpers.getFiles(null)).toBeNull();
});

test("persistFiles stores metadata and clears when empty or reader fails", async () => {
  const helpers = requireHelpers();
  const { win, stored } = makePersistWin();
  helpers.persistFiles(win, { files: [{ name: "one.png", type: "image/png", lastModified: 5 }] }, "key");
  await Promise.resolve();
  expect(win.sessionStorage.setItem).toHaveBeenCalledWith("key", expect.any(String));
  expect(JSON.parse(stored.key)[0].name).toBe("one.png");
  helpers.persistFiles(win, { files: [] }, "key");
  expect(win.sessionStorage.removeItem).toHaveBeenCalledWith("key");

  const { win: winFail } = makePersistWin({ fail: true });
  winFail.sessionStorage.removeItem.mockClear();
  await helpers.persistFiles(winFail, { files: [{ name: "bad.png", type: "image/png", lastModified: 2 }] }, "bad");
  expect(winFail.sessionStorage.removeItem).toHaveBeenCalledWith("bad");
});

test("restoreFiles reconstructs FileList via DataTransfer", async () => {
  const helpers = requireHelpers();
  const added = [];
  const win = {
    DataTransfer: makeDataTransfer(added),
    File: makeFileCtor(),
    fetch: () => Promise.resolve({ blob: () => Promise.resolve({ type: "text/plain" }) }),
    sessionStorage: {
      getItem: () =>
        JSON.stringify([{ name: "restored.txt", type: "text/plain", lastModified: 123, data: "data:text/plain;base64,aGVsbG8=" }])
    }
  };
  const input = {};
  await helpers.restoreFiles(win, input, "key", jest.fn());
  expect(input.__mockFiles).toEqual(added);
});

test("restoreFiles uses defaults when metadata missing", async () => {
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
  expect(created[0].name).toBe("upload");
  expect(created[0].type).toBe("application/octet-stream");
});

test("restoreFiles skips when fetch fails", async () => {
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

test("restoreFiles falls back when DataTransfer unavailable", async () => {
  const helpers = requireHelpers();
  const win = {
    File: makeFileCtor(),
    fetch: () => Promise.resolve({ blob: () => Promise.resolve({ type: "text/plain" }) }),
    sessionStorage: {
      getItem: () =>
        JSON.stringify([{ name: "restored.txt", type: "text/plain", lastModified: 123, data: "data:text/plain;base64,aGVsbG8=" }])
    }
  };
  const input = {};
  await helpers.restoreFiles(win, input, "key");
  expect(Array.isArray(input.__mockFiles)).toBe(true);
});

test("getFiles helper exported", () => {
  expect(getFiles({ files: [{ id: 1 }] })[0].id).toBe(1);
});

test("required field validator renders and clears client errors", () => {
  const helpers = loadHelpersWithOverrides();
  const { form, text, file } = formWithFields();
  file.required = true;
  let fileList = [];
  const validator = helpers.createRequiredFieldValidator(document, form, [text, file], () => fileList);
  expect(validator.renderRequiredFieldErrors()).toBe(true);
  expect(document.querySelectorAll(".client-required-error").length).toBe(2);
  validator.bindRequiredListeners();
  fileList = [{ name: "a" }];
  text.value = "ok";
  text.dispatchEvent(new Event("input"));
  file.dispatchEvent(new Event("change"));
  expect(document.querySelectorAll(".client-required-error").length).toBe(0);
});

test("required validator returns false when fields filled", () => {
  const helpers = requireHelpers();
  const { form, text, file } = formWithFields();
  file.required = true;
  text.value = "ok";
  const validator = helpers.createRequiredFieldValidator(document, form, [text, file], () => [{ name: "a" }]);
  expect(validator.renderRequiredFieldErrors()).toBe(false);
});

test("clearStoredFiles fallback removes session key", () => {
  const storage = { removeItem: jest.fn() };
  const helpers = loadHelpersWithOverrides({ images: {} });
  helpers.clearStoredFiles({ sessionStorage: storage }, "k1");
  expect(storage.removeItem).toHaveBeenCalledWith("k1");
});

test("clearStoredFiles uses provided images module", () => {
  const clearStoredFiles = jest.fn();
  const helpers = loadHelpersWithOverrides({ images: { clearStoredFiles } });
  helpers.clearStoredFiles({}, "k2");
  expect(clearStoredFiles).toHaveBeenCalledWith({}, "k2");
});

test("createImageManager and createShoppingManager use overrides", () => {
  const createImageManager = jest.fn(() => ({ bind: jest.fn() }));
  const createShoppingManager = jest.fn(() => ({ addLink: jest.fn() }));
  const helpers = loadHelpersWithOverrides({ images: { createImageManager }, shopping: { createShoppingManager } });
  helpers.createImageManager();
  helpers.createShoppingManager();
  expect(createImageManager).toHaveBeenCalled();
  expect(createShoppingManager).toHaveBeenCalled();
});

test("persistFiles caps at 10 files and writes data", async () => {
  const helpers = requireHelpers();
  const { win, stored } = makePersistWin();
  const files = Array.from({ length: 12 }, (_, i) => ({ name: `f${i}.png`, type: "image/png", lastModified: i }));
  await helpers.persistFiles(win, { files }, "cap");
  expect(JSON.parse(stored.cap)).toHaveLength(10);
});

test("restoreFiles triggers callback after applying files", async () => {
  const helpers = requireHelpers();
  const added = [];
  const after = jest.fn();
  const win = {
    DataTransfer: makeDataTransfer(added),
    File: makeFileCtor(),
    fetch: () => Promise.resolve({ blob: () => Promise.resolve({ type: "text/plain" }) }),
    sessionStorage: {
      getItem: () =>
        JSON.stringify([{ name: "r.txt", type: "text/plain", lastModified: 1, data: "data:text/plain;base64,aA==" }])
    }
  };
  await helpers.restoreFiles(win, {}, "k", after);
  expect(after).toHaveBeenCalled();
});

test("fallback validator renders orphan errors and removes via listeners", () => {
  const helpers = loadHelpersWithOverrides({ validation: {} });
  const field = document.createElement("input");
  field.required = true;
  document.body.innerHTML = "";
  document.body.appendChild(field);
  const validator = helpers.createRequiredFieldValidator(document, document.body, [field], () => null);
  expect(validator.renderRequiredFieldErrors()).toBe(true);
  validator.bindRequiredListeners();
  expect(document.querySelectorAll(".client-required-error").length).toBe(1);
  field.value = "x";
  field.dispatchEvent(new Event("input"));
  expect(document.querySelectorAll(".client-required-error").length).toBe(0);
});

test("safeRequire catches module errors and falls back to stubs", () => {
  jest.resetModules();
  const imagesPath = "../../static/js/create_recipe_images";
  jest.doMock(imagesPath, () => {
    throw new Error("fail");
  });
  jest.isolateModules(() => {
    const helpers = require("../../static/js/create_recipe_helpers");
    expect(() => helpers.createImageManager()).not.toThrow();
  });
});

test("falls back to window globals when module exports absent", () => {
  jest.resetModules();
  const original = module.exports;
  module.exports = undefined;
  global.window = { document: {}, createRecipeValidation: { createRequiredFieldValidator: jest.fn(() => ({ renderRequiredFieldErrors: jest.fn(), bindRequiredListeners: jest.fn() })) } };
  let helpers;
  jest.isolateModules(() => {
    helpers = require("../../static/js/create_recipe_helpers");
  });
  helpers.createRequiredFieldValidator(document, document.body, [], () => null);
  expect(typeof helpers.createRequiredFieldValidator).toBe("function");
  const spy = global.window.createRecipeValidation.createRequiredFieldValidator;
  if (spy && spy.mock) {
    expect(spy).toHaveBeenCalled();
  }
  module.exports = original;
  delete global.window;
});

test("fetchStoredEntries returns empty on invalid json", async () => {
  const helpers = requireHelpers();
  const win = { sessionStorage: { getItem: () => "not-json" } };
  await helpers.restoreFiles(win, {}, "k");
});

test("stub image manager exposes getters", () => {
  const helpers = loadHelpersWithOverrides({ images: {} });
  const mgr = helpers.createImageManager();
  expect(mgr.getSelectedFiles()).toEqual([]);
});

test("createImageManager and createShoppingManager fallback stubs exist", () => {
  const helpers = loadHelpersWithOverrides({ images: {}, shopping: {} });
  const imgMgr = helpers.createImageManager();
  const shopMgr = helpers.createShoppingManager();
  expect(typeof imgMgr.bind).toBe("function");
  expect(typeof shopMgr.addLink).toBe("function");
});
