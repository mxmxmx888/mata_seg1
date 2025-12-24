(function (global) {
  function initPostLightbox(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    const doc = w.document;
    const thumbs = Array.from(doc.querySelectorAll(".js-gallery-image"));
    if (!thumbs.length) return;

    const lightbox = doc.getElementById("lightbox");
    const lightboxImg = doc.getElementById("lightbox-image");
    const body = doc.body;
    const btnPrev = lightbox.querySelector(".lightbox-arrow--left");
    const btnNext = lightbox.querySelector(".lightbox-arrow--right");
    const backdrop = lightbox.querySelector(".lightbox-backdrop");

    let currentIndex = 0;
    let isOpen = false;

    function showImage(index) {
      const count = thumbs.length;
      currentIndex = (index + count) % count;
      const img = thumbs[currentIndex];
      const src = img.dataset.fullsrc || img.src;
      lightboxImg.src = src;
    }

    function openLightbox(index) {
      showImage(index);
      lightbox.classList.remove("d-none");
      body.classList.add("lightbox-open");
      isOpen = true;
    }

    function closeLightbox() {
      lightbox.classList.add("d-none");
      body.classList.remove("lightbox-open");
      isOpen = false;
    }

    thumbs.forEach((img, idx) => {
      img.addEventListener("click", (event) => {
        event.preventDefault();
        openLightbox(idx);
      });
    });

    backdrop.addEventListener("click", closeLightbox);

    btnPrev.addEventListener("click", () => showImage(currentIndex - 1));
    btnNext.addEventListener("click", () => showImage(currentIndex + 1));

    doc.addEventListener("keydown", (event) => {
      if (!isOpen) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        showImage(currentIndex - 1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        showImage(currentIndex + 1);
      } else if (event.key === "Escape") {
        closeLightbox();
      }
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initPostLightbox };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initPostLightbox(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
