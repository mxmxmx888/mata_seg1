(() => {
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" && window.document ? window : null;

const resolveWindow = (win) => {
  const candidate = win || globalWindow;
  return candidate && candidate.document ? candidate : null;
};

const buildLightboxState = (doc) => {
  const thumbs = Array.from(doc.querySelectorAll(".js-gallery-image"));
  if (!thumbs.length) return null;
  const lightbox = doc.getElementById("lightbox");
  return {
    thumbs,
    lightbox,
    lightboxImg: doc.getElementById("lightbox-image"),
    body: doc.body,
    btnPrev: lightbox ? lightbox.querySelector(".lightbox-arrow--left") : null,
    btnNext: lightbox ? lightbox.querySelector(".lightbox-arrow--right") : null,
    backdrop: lightbox ? lightbox.querySelector(".lightbox-backdrop") : null,
    currentIndex: 0,
    isOpen: false
  };
};

const showImage = (state, index) => {
  const count = state.thumbs.length;
  state.currentIndex = (index + count) % count;
  const img = state.thumbs[state.currentIndex];
  const src = img.dataset.fullsrc || img.src;
  if (state.lightboxImg) {
    state.lightboxImg.src = src;
  }
};

const openLightbox = (state, index) => {
  showImage(state, index);
  if (state.lightbox) state.lightbox.classList.remove("d-none");
  state.body.classList.add("lightbox-open");
  state.isOpen = true;
};

const closeLightbox = (state) => {
  if (state.lightbox) state.lightbox.classList.add("d-none");
  state.body.classList.remove("lightbox-open");
  state.isOpen = false;
};

const wireThumbs = (state) => {
  state.thumbs.forEach((img, idx) => {
    img.addEventListener("click", (event) => {
      event.preventDefault();
      openLightbox(state, idx);
    });
  });
};

const wireBackdrop = (state) => {
  if (state.backdrop) {
    state.backdrop.addEventListener("click", () => closeLightbox(state));
  }
};

const wireArrowControls = (state) => {
  if (state.btnPrev) state.btnPrev.addEventListener("click", () => showImage(state, state.currentIndex - 1));
  if (state.btnNext) state.btnNext.addEventListener("click", () => showImage(state, state.currentIndex + 1));
};

const wireKeyboard = (state) => {
  state.body.ownerDocument.addEventListener("keydown", (event) => {
    if (!state.isOpen) return;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showImage(state, state.currentIndex - 1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      showImage(state, state.currentIndex + 1);
    } else if (event.key === "Escape") {
      closeLightbox(state);
    }
  });
};

const initPostLightbox = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document) return;
  const state = buildLightboxState(w.document);
  if (!state || !state.lightbox) return;
  if (state.lightbox.dataset.lightboxInitialized === "1") return;
  state.lightbox.dataset.lightboxInitialized = "1";
  wireThumbs(state);
  wireBackdrop(state);
  wireArrowControls(state);
  wireKeyboard(state);
};

const autoInitPostLightbox = () => {
  const w = resolveWindow();
  if (!w) return;
  const runInit = () => initPostLightbox(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initPostLightbox };
}

/* istanbul ignore next */
autoInitPostLightbox();
})();
