{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const helpers = (() => {
  if (hasModuleExports) return require("./create_recipe_helpers");
  return globalWindow && globalWindow.createRecipeHelpers ? globalWindow.createRecipeHelpers : {};
})();

const normalizeUrl = helpers.normalizeUrl || ((url) => (/^https?:\/\//i.test(url || "") ? url : url ? "https://" + url : ""));
const setInputFiles = helpers.setInputFiles || (() => {});
const getFiles = helpers.getFiles || (() => null);
const noop = () => {};
const noopPromise = () => Promise.resolve();
const persistFiles = helpers.persistFiles || noopPromise;
const restoreFiles = helpers.restoreFiles || noopPromise;
const clearStoredFiles = helpers.clearStoredFiles || noop;
const createRequiredFieldValidator = helpers.createRequiredFieldValidator || (() => ({
  renderRequiredFieldErrors: () => false,
  bindRequiredListeners: noop,
}));
const createImageManager = helpers.createImageManager || (() => ({
  bind: noop,
  restoreFromStorage: noop,
  persistSelection: noop,
  renderImagesList: noop,
}));
const createShoppingManager = helpers.createShoppingManager || (() => ({
  bind: noop,
  bootstrapExisting: noop,
  renderList: noop,
  syncShoppingField: noop,
  syncShopImagesInput: noop,
}));

const parseJsonSafe = (value) => {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (err) {
    return null;
  }
};

const readExistingShoppingItems = (listBox, inlineJson) => {
  const candidates = [inlineJson && inlineJson.textContent, listBox && listBox.dataset.shoppingItems, "[]"];
  const parsed = candidates.map(parseJsonSafe).find((value) => value !== null);
  const normalized = typeof parsed === "string" ? parseJsonSafe(parsed) : parsed;
  return Array.isArray(normalized) ? normalized : [];
};

const cleanIngredientsField = (ingredientsField) => {
  const manual = (ingredientsField.value || "").trim();
  const lines = manual ? manual.split(/\r?\n/).map((l) => l.trim()).filter(Boolean) : [];
  ingredientsField.value = lines.join("\n");
};

const imageManagerFor = (ctx) =>
  createImageManager({
    w: ctx.w,
    doc: ctx.doc,
    imageInput: ctx.imageInput,
    imageList: ctx.imageList,
    storageKey: ctx.IMG_STORAGE_KEY,
    setInputFiles,
    getFiles,
    persistFiles,
    restoreFiles,
  });

const shoppingManagerFor = (ctx) =>
  createShoppingManager({
    w: ctx.w,
    doc: ctx.doc,
    itemInput: ctx.itemInput,
    linkInput: ctx.linkInput,
    addBtn: ctx.addBtn,
    listBox: ctx.listBox,
    shoppingField: ctx.shoppingField,
    shopImageInput: ctx.shopImageInput,
    shopImageList: ctx.shopImageList,
    normalizeUrl,
    setInputFiles,
    getFiles,
    existingShoppingItems: ctx.existingShoppingItems,
  });

const buildManagers = (ctx) => ({
  validator: createRequiredFieldValidator(ctx.doc, ctx.formEl, ctx.requiredFields, getFiles),
  imageManager: imageManagerFor(ctx),
  shoppingManager: shoppingManagerFor(ctx),
});

const resolveRequiredElements = (doc) => {
  const formEl = doc.querySelector(".create-recipe-card form");
  const ids = ["id_ingredients_text", "shop-item", "shop-link", "add-shop-link", "shop-list", "id_shopping_links_text"];
  const [ingredientsField, itemInput, linkInput, addBtn, listBox, shoppingField] = ids.map((id) => doc.getElementById(id));
  if (!formEl || [ingredientsField, itemInput, linkInput, addBtn, listBox, shoppingField].includes(null)) return null;
  return { formEl, ingredientsField, itemInput, linkInput, addBtn, listBox, shoppingField };
};

const gatherContext = (w) => {
  if (!w || !w.document) return null;
  const doc = w.document;
  const requiredEls = resolveRequiredElements(doc);
  if (!requiredEls) return null;
  const inlineJson = doc.getElementById("existing-shopping-items");
  const imageInput = doc.getElementById("id_images");
  const requiredFields = Array.from(requiredEls.formEl.querySelectorAll("[required]"));
  if (imageInput) {
    imageInput.setAttribute("required", "required");
    requiredFields.push(imageInput);
  }
  const extras = {
    imageInput,
    imageList: doc.getElementById("image-file-list"),
    shopImageInput: doc.getElementById("id_shop_images"),
    shopImageList: doc.getElementById("shop-image-file-list"),
    existingShoppingItems: readExistingShoppingItems(requiredEls.listBox, inlineJson),
    requiredFields,
    IMG_STORAGE_KEY: "create-recipe-images",
    isBound: requiredEls.formEl.dataset.formBound === "true",
    hasErrors: requiredEls.formEl.dataset.formHasErrors === "true",
  };
  return { w, doc, ...requiredEls, ...extras };
};

const bindManagers = (ctx, validator, shoppingManager, imageManager) => {
  validator.bindRequiredListeners();
  shoppingManager.bind();
  imageManager.bind();
  if (!ctx.isBound) {
    clearStoredFiles(ctx.w, ctx.IMG_STORAGE_KEY);
  } else if (ctx.hasErrors) {
    imageManager.restoreFromStorage();
  }
  shoppingManager.bootstrapExisting();
  shoppingManager.renderList();
};

const handleSubmit = (ctx, validator, shoppingManager, imageManager) => {
  ctx.formEl.addEventListener("submit", (event) => {
    if (validator.renderRequiredFieldErrors()) {
      event.preventDefault();
      return;
    }
    cleanIngredientsField(ctx.ingredientsField);
    shoppingManager.syncShoppingField();
    shoppingManager.syncShopImagesInput();
    imageManager.persistSelection();
  });
};

const initCreateRecipe = (win) => {
  const ctx = gatherContext(win || globalWindow);
  if (!ctx) return;
  const managers = buildManagers(ctx);
  bindManagers(ctx, managers.validator, managers.shoppingManager, managers.imageManager);
  handleSubmit(ctx, managers.validator, managers.shoppingManager, managers.imageManager);
};

const autoInit = () => {
  const w = globalWindow;
  if (!w || !w.document) return;
  const runInit = () => initCreateRecipe(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initCreateRecipe, normalizeUrl };
}

/* istanbul ignore next */
autoInit();
}
