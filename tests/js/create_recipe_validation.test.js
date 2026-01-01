const { createRequiredFieldValidator } = require("../../static/js/create_recipe_validation");

const makeField = (type = "text") => {
  const el = document.createElement("input");
  el.type = type;
  el.required = true;
  return el;
};

afterEach(() => {
  jest.clearAllMocks();
});

test("renders errors for missing fields and clears on events", () => {
  const form = document.createElement("form");
  const inputField = makeField();
  const fileField = makeField("file");
  form.appendChild(inputField);
  form.appendChild(fileField);
  const validator = createRequiredFieldValidator(document, form, [inputField, fileField], () => []);
  expect(validator.renderRequiredFieldErrors()).toBe(true);
  expect(form.querySelectorAll(".client-required-error").length).toBe(2);
  validator.bindRequiredListeners();
  inputField.dispatchEvent(new Event("input"));
  fileField.dispatchEvent(new Event("change"));
  expect(form.querySelectorAll(".client-required-error").length).toBe(0);
});

test("treats file field as satisfied when getFiles returns items", () => {
  const form = document.createElement("form");
  const fileField = makeField("file");
  form.appendChild(fileField);
  const validator = createRequiredFieldValidator(document, form, [fileField], () => ["file"]);
  expect(validator.renderRequiredFieldErrors()).toBe(false);
  expect(form.querySelector(".client-required-error")).toBeNull();
});

test("returns false when form is missing", () => {
  const validator = createRequiredFieldValidator(document, null, [], () => []);
  expect(validator.renderRequiredFieldErrors()).toBe(false);
});
