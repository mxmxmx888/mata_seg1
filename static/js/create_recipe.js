(function (global) {
  /* istanbul ignore next */
  const helpers = (() => {
    if (typeof module !== "undefined" && module.exports) {
      return require("./create_recipe_helpers");
    }
    return global && global.createRecipeHelpers ? global.createRecipeHelpers : {};
  })();
  const normalizeUrl =
    helpers.normalizeUrl ||
    /* istanbul ignore next */ ((url) => (/^https?:\/\//i.test(url || "") ? url : url ? "https://" + url : ""));
  const setInputFiles = helpers.setInputFiles || /* istanbul ignore next */ (() => {});
  const getFiles = helpers.getFiles || /* istanbul ignore next */ (() => null);
  const persistFiles = helpers.persistFiles || /* istanbul ignore next */ (() => {});
  const restoreFiles = helpers.restoreFiles || /* istanbul ignore next */ (() => Promise.resolve());
  const clearStoredFiles = helpers.clearStoredFiles || /* istanbul ignore next */ (() => {});
  const createRequiredFieldValidator =
    helpers.createRequiredFieldValidator ||
    /* istanbul ignore next */ (() => ({
      renderRequiredFieldErrors: () => false,
      bindRequiredListeners: () => {}
    }));
  const createImageManager =
    helpers.createImageManager ||
    /* istanbul ignore next */ (() => ({
      bind: () => {},
      restoreFromStorage: () => {},
      persistSelection: () => {},
      renderImagesList: () => {}
    }));
  const createShoppingManager =
    helpers.createShoppingManager ||
    /* istanbul ignore next */ (() => ({
      bind: () => {},
      bootstrapExisting: () => {},
      renderList: () => {},
      syncShoppingField: () => {},
      syncShopImagesInput: () => {}
    }));

  function cleanIngredientsField(ingredientsField) {
    const manual = (ingredientsField.value || "").trim();
    const manualLines = manual ? manual.split(/\r?\n/).map((l) => l.trim()).filter(Boolean) : [];
    ingredientsField.value = manualLines.join("\n");
  }

  function initCreateRecipe(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    /* istanbul ignore next */
    if (!w || !w.document) return;
    const doc = w.document;

    const formEl = doc.querySelector(".create-recipe-card form");
    const imageInput = doc.getElementById("id_images");
    const imageList = doc.getElementById("image-file-list");
    const shopImageInput = doc.getElementById("id_shop_images");
    const shopImageList = doc.getElementById("shop-image-file-list");
    const shoppingField = doc.getElementById("id_shopping_links_text");
    const ingredientsField = doc.getElementById("id_ingredients_text");
    const itemInput = doc.getElementById("shop-item");
    const linkInput = doc.getElementById("shop-link");
    const addBtn = doc.getElementById("add-shop-link");
    const listBox = doc.getElementById("shop-list");
    const inlineJson = doc.getElementById("existing-shopping-items");
    let existingShoppingItems = [];
    if (inlineJson && inlineJson.textContent) {
      try {
        existingShoppingItems = JSON.parse(inlineJson.textContent);
      } catch (err) {
        existingShoppingItems = [];
      }
    } else {
      const shoppingItemsData = listBox && listBox.dataset.shoppingItems ? listBox.dataset.shoppingItems : "[]";
      try {
        existingShoppingItems = JSON.parse(shoppingItemsData);
      } catch (err) {
        existingShoppingItems = [];
      }
    }
    if (typeof existingShoppingItems === "string") {
      try {
        existingShoppingItems = JSON.parse(existingShoppingItems);
      } catch (err) {
        existingShoppingItems = [];
      }
    }
    if (!Array.isArray(existingShoppingItems)) {
      existingShoppingItems = [];
    }
    const isBound = formEl && formEl.dataset.formBound === "true";
    const hasErrors = formEl && formEl.dataset.formHasErrors === "true";
    const requiredFields = formEl ? Array.from(formEl.querySelectorAll("[required]")) : [];
    const IMG_STORAGE_KEY = "create-recipe-images";

    /* istanbul ignore next */
    if (!formEl || !ingredientsField || !itemInput || !linkInput || !addBtn || !listBox || !shoppingField) return;

    if (imageInput) {
      imageInput.setAttribute("required", "required");
      requiredFields.push(imageInput);
    }

    const validator = createRequiredFieldValidator(doc, formEl, requiredFields, getFiles);
    const imageManager = createImageManager({
      w,
      doc,
      imageInput,
      imageList,
      storageKey: IMG_STORAGE_KEY,
      setInputFiles,
      getFiles,
      persistFiles,
      restoreFiles
    });
    const shoppingManager = createShoppingManager({
      w,
      doc,
      itemInput,
      linkInput,
      addBtn,
      listBox,
      shoppingField,
      shopImageInput,
      shopImageList,
      normalizeUrl,
      setInputFiles,
      getFiles,
      existingShoppingItems
    });

    validator.bindRequiredListeners();
    shoppingManager.bind();
    imageManager.bind();

    if (!isBound) {
      clearStoredFiles(w, IMG_STORAGE_KEY);
    } else if (hasErrors) {
      imageManager.restoreFromStorage();
    }

    shoppingManager.bootstrapExisting();
    shoppingManager.renderList();

    formEl.addEventListener("submit", (event) => {
      const hasClientErrors = validator.renderRequiredFieldErrors();
      if (hasClientErrors) {
        event.preventDefault();
        return;
      }
      cleanIngredientsField(ingredientsField);
      shoppingManager.syncShoppingField();
      shoppingManager.syncShopImagesInput();
      imageManager.persistSelection();
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      initCreateRecipe,
      normalizeUrl
    };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initCreateRecipe(global);
    /* istanbul ignore next */
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
