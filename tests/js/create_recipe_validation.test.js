const { createRequiredFieldValidator } = require("../../static/js/create_recipe_validation");

describe("create_recipe_validation", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test("renders errors for missing fields and clears on events", () => {
    const form = document.createElement("form");
    const inputField = document.createElement("input");
    inputField.required = true;
    const fileField = document.createElement("input");
    fileField.type = "file";
    fileField.required = true;
    form.appendChild(inputField);
    form.appendChild(fileField);

    const validator = createRequiredFieldValidator(document, form, [inputField, fileField], () => []);
    const hasErrors = validator.renderRequiredFieldErrors();
    expect(hasErrors).toBe(true);
    expect(form.querySelectorAll(".client-required-error").length).toBe(2);

    validator.bindRequiredListeners();
    inputField.dispatchEvent(new Event("input"));
    fileField.dispatchEvent(new Event("change"));
    expect(form.querySelectorAll(".client-required-error").length).toBe(0);
  });

  test("treats file field as satisfied when getFiles returns items", () => {
    const form = document.createElement("form");
    const fileField = document.createElement("input");
    fileField.type = "file";
    fileField.required = true;
    form.appendChild(fileField);

    const validator = createRequiredFieldValidator(document, form, [fileField], () => ["file"]);
    const hasErrors = validator.renderRequiredFieldErrors();
    expect(hasErrors).toBe(false);
    expect(form.querySelector(".client-required-error")).toBeNull();
  });

  test("returns false when form is missing", () => {
    const validator = createRequiredFieldValidator(document, null, [], () => []);
    expect(validator.renderRequiredFieldErrors()).toBe(false);
  });
});
