{
const hasModuleExports = typeof module !== "undefined" && module.exports;
const globalWindow = typeof window !== "undefined" ? window : null;

const resolveWindow = (win) => win || globalWindow;
const markInitialized = (w, flag) => {
  if (!w || w[flag]) return false;
  w[flag] = true;
  return true;
};

const cloneSlide = (slide, cloneIndex) => {
  const clone = slide.cloneNode(true);
  clone.setAttribute("data-clone", "true");
  clone.setAttribute("data-clone-index", String(cloneIndex));
  return clone;
};

const buildDots = (doc, slides, dotsContainer) => {
  const dots = [];
  if (!dotsContainer) return dots;
  dotsContainer.innerHTML = "";
  slides.forEach((_s, i) => {
    const dot = doc.createElement("button");
    dot.type = "button";
    dot.className = "browse-carousel-dot";
    dot.setAttribute("aria-label", `Go to slide ${i + 1}`);
    dotsContainer.appendChild(dot);
    dots.push(dot);
  });
  return dots;
};

const firstRect = (el) => {
  if (el && typeof el.getBoundingClientRect === "function") {
    return el.getBoundingClientRect();
  }
  return { width: el ? el.offsetWidth || 0 : 0, left: 0 };
};

const positionFor = (allSlides, realSlide) => {
  const baseRect = firstRect(allSlides[0]);
  const slideRect = firstRect(realSlide);
  return slideRect.left - baseRect.left;
};

const markActive = (dots, hoverTip, realIndex) => {
  dots.forEach((dot, i) => {
    dot.classList.toggle("active", i === realIndex);
  });
  if (hoverTip) hoverTip.dataset.visible = "false";
};

const updateHoverTip = (hoverTip, trackRect, event) => {
  if (!hoverTip || !trackRect) return;
  const isLeft = event.clientX < trackRect.left + trackRect.width / 2;
  hoverTip.textContent = isLeft ? "Previous" : "Next";
  hoverTip.style.transform = `translate(${event.clientX - trackRect.left}px, ${event.clientY - trackRect.top}px)`;
  hoverTip.dataset.visible = "true";
};

const directionFromClick = (track, event) => {
  const rect = track?.getBoundingClientRect?.();
  if (!rect || !rect.width) return null;
  return event.clientX < rect.left + rect.width / 2 ? -1 : 1;
};

const goTo = (ctx, realIndex, animate = true) => {
  const target = ctx.slides[realIndex];
  if (!target) return;
  ctx.index = realIndex;
  const offset = positionFor(ctx.allSlides, target);
  if (typeof ctx.viewport.scrollTo === "function") {
    ctx.viewport.scrollTo({ left: offset, behavior: animate ? "smooth" : "auto" });
  } else {
    ctx.viewport.scrollLeft = offset;
  }
  markActive(ctx.dots, ctx.hoverTip, realIndex);
};

const startAutoplay = (ctx) => {
  if (!ctx.allowAutoplay) return;
  stopAutoplay(ctx);
  ctx.timer = ctx.w.setInterval(() => {
    goTo(ctx, (ctx.index + 1) % ctx.slides.length, true);
  }, 4000);
};

const stopAutoplay = (ctx) => {
  if (ctx.timer) {
    ctx.w.clearInterval(ctx.timer);
    ctx.timer = null;
  }
};

const attachCarouselEvents = (ctx, track, carousel) => {
  ctx.dots.forEach((dot, i) => dot.addEventListener("click", () => goTo(ctx, i, false)));
  track.addEventListener("mousemove", (event) => updateHoverTip(ctx.hoverTip, track.getBoundingClientRect?.(), event));
  track.addEventListener("mouseenter", (event) => updateHoverTip(ctx.hoverTip, track.getBoundingClientRect?.(), event));
  track.addEventListener("mouseleave", () => ctx.hoverTip && (ctx.hoverTip.dataset.visible = "false"));
  const clickHandler = (event) => {
    const dir = directionFromClick(track, event);
    if (!dir) return;
    const next = dir > 0 ? (ctx.index + 1) % ctx.slides.length : Math.max(0, ctx.index - 1);
    goTo(ctx, next, true);
  };
  track.addEventListener("click", clickHandler);
  ctx.viewport.addEventListener("click", clickHandler);
  carousel.addEventListener("mouseenter", () => stopAutoplay(ctx));
  carousel.addEventListener("mouseleave", () => startAutoplay(ctx));
};

const buildCarousel = (w, carousel) => {
  const doc = w.document;
  const viewport = carousel.querySelector(".browse-carousel-viewport");
  const track = carousel.querySelector(".browse-carousel-track");
  const hoverTip = carousel.querySelector(".browse-hover-tip");
  if (!viewport || !track) return;
  const slides = Array.from(track.children);
  if (!slides.length) return;
  const prependClones = slides.map((slide, i) => cloneSlide(slide, -slides.length + i));
  const appendClones = slides.map((slide, i) => cloneSlide(slide, slides.length + i));
  track.innerHTML = "";
  prependClones.forEach((c) => track.appendChild(c));
  slides.forEach((s) => track.appendChild(s));
  appendClones.forEach((c) => track.appendChild(c));
  const allSlides = Array.from(track.children);
  const dots = buildDots(doc, slides, carousel.querySelector(".browse-carousel-dots"));
  const ctx = { w, viewport, slides, allSlides, dots, hoverTip, allowAutoplay: carousel.dataset.autoplay === "true", index: 0, timer: null };
  attachCarouselEvents(ctx, track, carousel);
  goTo(ctx, 0, false);
  startAutoplay(ctx);
};

const initHomeBrowseCarousel = (win) => {
  const w = resolveWindow(win);
  if (!w || !w.document || !markInitialized(w, "__homeBrowseCarouselInitialized")) return;
  const carousels = w.document.querySelectorAll(".browse-carousel");
  carousels.forEach((carousel) => buildCarousel(w, carousel));
};

const autoInit = () => {
  const w = resolveWindow();
  if (!w || !w.document) return;
  const runInit = () => initHomeBrowseCarousel(w);
  if (w.document.readyState === "loading") {
    w.document.addEventListener("DOMContentLoaded", runInit, { once: true });
  } else {
    runInit();
  }
};

if (hasModuleExports) {
  module.exports = { initHomeBrowseCarousel };
}

/* istanbul ignore next */
autoInit();
}
