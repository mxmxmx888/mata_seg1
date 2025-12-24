(function (global) {
  function initHomeBrowseCarousel(win) {
    const w = win || (typeof window !== "undefined" ? window : undefined);
    if (!w || !w.document) return;
    if (w.__homeBrowseCarouselInitialized) return;
    w.__homeBrowseCarouselInitialized = true;

    const doc = w.document;
    const carousels = doc.querySelectorAll(".browse-carousel");
    if (!carousels.length) return;

    carousels.forEach((carousel) => {
      const viewport = carousel.querySelector(".browse-carousel-viewport");
      const track = carousel.querySelector(".browse-carousel-track");
      const hoverTip = carousel.querySelector(".browse-hover-tip");
      if (!viewport || !track) return;

      const slides = Array.from(track.children);
      if (!slides.length) return;

      function cloneSlide(slide, cloneIndex) {
        const clone = slide.cloneNode(true);
        clone.setAttribute("data-clone", "true");
        clone.setAttribute("data-clone-index", String(cloneIndex));
        return clone;
      }

      const prependClones = slides.map((slide, i) => cloneSlide(slide, -slides.length + i));
      const appendClones = slides.map((slide, i) => cloneSlide(slide, slides.length + i));

      track.innerHTML = "";
      prependClones.forEach((c) => track.appendChild(c));
      slides.forEach((s) => track.appendChild(s));
      appendClones.forEach((c) => track.appendChild(c));

      const allSlides = Array.from(track.children);
      const dotsContainer = carousel.querySelector(".browse-carousel-dots");
      const dots = [];
      if (dotsContainer) {
        dotsContainer.innerHTML = "";
        slides.forEach((_s, i) => {
          const dot = doc.createElement("button");
          dot.type = "button";
          dot.className = "browse-carousel-dot";
          dot.setAttribute("aria-label", `Go to slide ${i + 1}`);
          dotsContainer.appendChild(dot);
          dots.push(dot);
        });
      }

      let index = 0;
      let timer = null;
      const allowAutoplay = carousel.dataset.autoplay === "true";

      const firstRect = (el) => {
        if (el && typeof el.getBoundingClientRect === "function") {
          return el.getBoundingClientRect();
        }
        return { width: el.offsetWidth || 0, left: 0 };
      };

      function positionFor(realSlide) {
        const baseRect = firstRect(allSlides[0]);
        const slideRect = firstRect(realSlide);
        return slideRect.left - baseRect.left;
      }

      function markActive(realIndex) {
        dots.forEach((dot, i) => {
          dot.classList.toggle("active", i === realIndex);
        });
        if (hoverTip) {
          hoverTip.dataset.visible = "false";
        }
      }

      function goTo(realIndex, animate = true) {
        if (!slides[realIndex]) return;
        index = realIndex;
        const target = slides[realIndex];
        const offset = positionFor(target);
        if (typeof viewport.scrollTo === "function") {
          viewport.scrollTo({ left: offset, behavior: animate ? "smooth" : "auto" });
        } else {
          viewport.scrollLeft = offset;
        }
        markActive(realIndex);
      }

      dots.forEach((dot, i) => {
        dot.addEventListener("click", () => {
          goTo(i, false);
        });
      });

      function showHoverTip() {
        if (hoverTip) hoverTip.dataset.visible = "true";
      }
      function hideHoverTip() {
        if (hoverTip) hoverTip.dataset.visible = "false";
      }
      track.addEventListener("mouseenter", showHoverTip);
      track.addEventListener("mouseleave", hideHoverTip);

      function startAutoplay() {
        if (!allowAutoplay) return;
        stopAutoplay();
        timer = w.setInterval(() => {
          const next = (index + 1) % slides.length;
          goTo(next, true);
        }, 4000);
      }
      function stopAutoplay() {
        if (timer) {
          w.clearInterval(timer);
          timer = null;
        }
      }

      carousel.addEventListener("mouseenter", stopAutoplay);
      carousel.addEventListener("mouseleave", startAutoplay);

      goTo(0, false);
      startAutoplay();
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initHomeBrowseCarousel };
  }

  /* istanbul ignore next */
  if (global && global.document) {
    const runInit = () => initHomeBrowseCarousel(global);
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", runInit, { once: true });
    } else {
      runInit();
    }
  }
})(typeof window !== "undefined" ? window : null);
