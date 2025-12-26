(function (global) {
  function createRequiredFieldValidator(doc, formEl, requiredFields, getFilesFn) {
    const getFilesSafe = typeof getFilesFn === "function" ? getFilesFn : () => null;
    const fields = requiredFields || [];

    function clearFieldError(field) {
      const container = field && (field.closest(".mb-3") || field.parentElement);
      /* istanbul ignore next */
      if (!container) return;
      container.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
    }

    function renderRequiredFieldErrors() {
      /* istanbul ignore next */
      if (!formEl) return false;
      let hasClientErrors = false;
      formEl.querySelectorAll(".client-required-error").forEach((msg) => msg.remove());
      fields.forEach((field) => {
        const candidateFiles = field.type === "file" ? getFilesSafe(field) : null;
        let isMissing = field.validity ? field.validity.valueMissing : !(field.value || "").trim();
        if (candidateFiles && candidateFiles.length) {
          isMissing = false;
        }
        if (!isMissing) {
          clearFieldError(field);
          return;
        }
        hasClientErrors = true;
        const message = doc.createElement("div");
        message.className = "client-required-error";
        message.textContent = "field required";
        const container = field.closest(".mb-3") || field.parentElement;
        const invalidFeedback = container ? container.querySelector(".invalid-feedback") : null;
        if (invalidFeedback) {
          invalidFeedback.insertAdjacentElement("beforebegin", message);
        } else if (container) {
          container.appendChild(message);
        } else {
          /* istanbul ignore next */
          field.insertAdjacentElement("afterend", message);
        }
      });
      return hasClientErrors;
    }

    function bindRequiredListeners() {
      fields.forEach((field) => {
        /* istanbul ignore next */
        field.addEventListener("input", () => clearFieldError(field));
        /* istanbul ignore next */
        field.addEventListener("change", () => clearFieldError(field));
      });
    }

    return { renderRequiredFieldErrors, bindRequiredListeners };
  }

  const api = { createRequiredFieldValidator };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  /* istanbul ignore next */
  if (global) {
    global.createRecipeValidation = api;
  }
})(typeof window !== "undefined" ? window : null);
