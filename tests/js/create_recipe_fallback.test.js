const { buildForm } = require("./support/createRecipeTestUtils");

describe("create_recipe fallback helpers", () => {
  beforeEach(() => {
    jest.resetModules();
  });

  test("handles missing helpers, bad shopping JSON, and error restore branch", () => {
    jest.doMock("../../static/js/create_recipe_helpers", () => ({}));
    buildForm({ bound: true, hasErrors: true });
    const listBox = document.getElementById("shop-list");
    listBox.dataset.shoppingItems = "\"abc\"";
    const inlineJson = document.createElement("div");
    inlineJson.id = "existing-shopping-items";
    inlineJson.textContent = "bad";
    document.body.appendChild(inlineJson);

    jest.isolateModules(() => {
      const { initCreateRecipe } = require("../../static/js/create_recipe");
      expect(() => initCreateRecipe(window)).not.toThrow();
    });
  });
});
