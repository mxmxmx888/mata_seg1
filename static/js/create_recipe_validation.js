{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalScope = typeof window !== "undefined" ? window : null;

const resolveFilesGetter = (fn) => (typeof fn === "function" ? fn : () => null);

const clearFieldError = (field) => {
  const container = field && (field.closest(".mb-3") || field.parentElement);
  if (!container) return;
  container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
};

const fieldMissing = (field, getFilesSafe) => {
  const candidateFiles = field.type === "file" ? getFilesSafe(field) : null;
  if (candidateFiles && candidateFiles.length) return false;
  if (field.validity) return field.validity.valueMissing;
  return !((field.value || "").trim());
};

const insertError = (doc, field, message) => {
  const container = field.closest(".mb-3") || field.parentElement;
  const msg = doc.createElement("div");
  msg.className = "client-required-error";
  msg.textContent = message;
  const invalid = container ? container.querySelector(".invalid-feedback") : null;
  if (invalid) {
    invalid.insertAdjacentElement("beforebegin", msg);
  } else if (container) {
    container.appendChild(msg);
  } else {
    field.insertAdjacentElement("afterend", msg);
  }
};

const renderRequiredFieldErrors = (doc, formEl, fields, getFilesSafe) => {
  if (!formEl) return false;
  formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
  let hasErrors = false;
  fields.forEach((field) => {
    if (!fieldMissing(field, getFilesSafe)) {
      clearFieldError(field);
      return;
    }
    hasErrors = true;
    insertError(doc, field, "field required");
  });
  return hasErrors;
};

const bindRequiredListeners = (fields) => {
  fields.forEach((field) => {
    field.addEventListener("input", () => clearFieldError(field));
    field.addEventListener("change", () => clearFieldError(field));
  });
};

const createRequiredFieldValidator = (doc, formEl, requiredFields, getFilesFn) => {
  const fields = requiredFields || [];
  const getFilesSafe = resolveFilesGetter(getFilesFn);
  return {
    renderRequiredFieldErrors: () => renderRequiredFieldErrors(doc, formEl, fields, getFilesSafe),
    bindRequiredListeners: () => bindRequiredListeners(fields),
  };
};

const api = { createRequiredFieldValidator };

if (hasModuleExports) {
  module.exports = api;
}

/* istanbul ignore next */
if (globalScope) {
  globalScope.createRecipeValidation = api;
}
}
