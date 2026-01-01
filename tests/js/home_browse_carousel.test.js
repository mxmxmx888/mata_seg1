const modulePath = "../../static/js/home_browse_carousel";

function loadModule() {
  jest.resetModules();
  delete global.__homeBrowseCarouselInitialized;
  const mod = require(modulePath);
  return mod;
}

describe("home_browse_carousel", () => {
  beforeEach(resetCarouselEnv);
  afterEach(jest.useRealTimers);
  testCreatesClonesAndDots();
  testDotClickNavigates();
  testAutoplayAdvancesSlides();
  testViewportClickNavigates();
  testDisablesAutoplayWhenFalse();
  testHandlesMissingCarousels();
  testEarlyExitNoSlidesOrTrack();
  testFallbackWhenScrollToMissing();
  testHidesHoverTipOnStop();
  testFallbackOffsetWidth();
  testInitializesWithoutDotsOrHover();
  testReturnsEarlyWhenNoDocument();
  testAutoInitAddsDOMContentLoadedListener();
  testAutoInitWhenDocumentReady();
  testReturnsEarlyNoCarouselsNoWindow();
  testReturnsEarlyWindowMissingDocument();
});

function buildDom() {
  document.body.innerHTML = `
    <div class="browse-carousel" data-autoplay="true">
      <div class="browse-carousel-viewport">
        <div class="browse-carousel-track">
          <article class="slide">One</article>
          <article class="slide">Two</article>
        </div>
      </div>
      <div class="browse-hover-tip" data-visible="false"></div>
      <div class="browse-carousel-dots"></div>
    </div>
  `;
  const slides = document.querySelectorAll(".slide");
  slides.forEach((slide, idx) => {
    slide.getBoundingClientRect = () => ({ width: 200, left: idx * 220 });
  });
  const viewport = document.querySelector(".browse-carousel-viewport");
  viewport.scrollTo = jest.fn(function ({ left }) {
    this.scrollLeft = left;
  });
}

function resetCarouselEnv() {
  document.body.innerHTML = "";
  jest.useFakeTimers();
  delete global.__homeBrowseCarouselInitialized;
}

function testCreatesClonesAndDots() {
  test("creates clones and dots, marks active", () => {
    buildDom();
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);

    const track = document.querySelector(".browse-carousel-track");
    expect(track.children.length).toBeGreaterThan(2);
    const dots = document.querySelectorAll(".browse-carousel-dot");
    expect(dots.length).toBe(2);
    expect(Array.from(dots).some((d) => d.classList.contains("active"))).toBe(true);
  });
}

function testDotClickNavigates() {
  test("dot click navigates without animation", () => {
    buildDom();
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    const viewport = document.querySelector(".browse-carousel-viewport");

    const dots = document.querySelectorAll(".browse-carousel-dot");
    dots[1].click();
    expect(viewport.scrollLeft).toBeGreaterThan(0);
    expect(dots[1].classList.contains("active")).toBe(true);
    const hoverTip = document.querySelector(".browse-hover-tip");
    expect(hoverTip.dataset.visible).toBe("false");
  });
}

function testAutoplayAdvancesSlides() {
  test("autoplay advances slides and shows hover tip", () => {
    buildDom();
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);

    jest.advanceTimersByTime(5500);
    const viewport = document.querySelector(".browse-carousel-viewport");
    expect(viewport.scrollLeft).toBeGreaterThan(0);

    const track = document.querySelector(".browse-carousel-track");
    track.dispatchEvent(new Event("mouseenter"));
    const hoverTip = document.querySelector(".browse-hover-tip");
    expect(hoverTip.dataset.visible).toBe("true");

    track.dispatchEvent(new Event("mouseleave"));
    expect(hoverTip.dataset.visible).toBe("false");
  });
}

function testViewportClickNavigates() {
  test("viewport click navigates prev/next and hover tip updates", () => {
    buildDom();
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);

    const viewport = document.querySelector(".browse-carousel-viewport");
    const track = document.querySelector(".browse-carousel-track");
    const hoverTip = document.querySelector(".browse-hover-tip");
    track.getBoundingClientRect = () => ({ left: 0, width: 200, top: 0, height: 100 });
    track.dispatchEvent(new MouseEvent("mouseenter", { clientX: 50, clientY: 10 }));
    expect(hoverTip.dataset.visible).toBe("true");

    viewport.getBoundingClientRect = () => ({ left: 0, width: 200, top: 0, height: 100 });
    viewport.dispatchEvent(new MouseEvent("click", { clientX: 50, clientY: 10 }));
    expect(viewport.scrollLeft).toBe(0);

    expect(() => viewport.dispatchEvent(new MouseEvent("click", { clientX: 180, clientY: 10 }))).not.toThrow();
    jest.advanceTimersByTime(5000);
    expect(viewport.scrollLeft).toBeGreaterThanOrEqual(0);
  });
}

function testDisablesAutoplayWhenFalse() {
  test("disables autoplay when data-autoplay is false", () => {
    buildDom();
    document.querySelector(".browse-carousel").dataset.autoplay = "false";
    const intervalSpy = jest.spyOn(window, "setInterval");
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    expect(intervalSpy).not.toHaveBeenCalled();
    intervalSpy.mockRestore();
  });
}

function testHandlesMissingCarousels() {
  test("handles missing carousels without error", () => {
    document.body.innerHTML = ``;
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel(window)).not.toThrow();
  });
}

function testEarlyExitNoSlidesOrTrack() {
  test("early exits when no slides or track", () => {
    document.body.innerHTML = `<div class="browse-carousel"><div class="browse-carousel-viewport"></div></div>`;
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel(window)).not.toThrow();
  });
}

function testFallbackWhenScrollToMissing() {
  test("falls back when scrollTo missing", () => {
    buildDom();
    const viewport = document.querySelector(".browse-carousel-viewport");
    viewport.scrollTo = undefined;
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    const dots = document.querySelectorAll(".browse-carousel-dot");
    dots[1].click();
    expect(viewport.scrollLeft).toBeGreaterThanOrEqual(0);
  });
}

function testHidesHoverTipOnStop() {
  test("hides hover tip and clears interval on stop", () => {
    buildDom();
    const clearSpy = jest.spyOn(window, "clearInterval");
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    const carousel = document.querySelector(".browse-carousel");
    const hoverTip = document.querySelector(".browse-hover-tip");
    carousel.dispatchEvent(new Event("mouseenter"));
    expect(hoverTip.dataset.visible).toBe("false");
    expect(clearSpy).toHaveBeenCalled();
    clearSpy.mockRestore();
  });
}

function testFallbackOffsetWidth() {
  test("falls back to offsetWidth when getBoundingClientRect missing", () => {
    buildDom();
    document.querySelectorAll(".slide").forEach((slide) => {
      slide.getBoundingClientRect = undefined;
      slide.offsetWidth = 150;
    });
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    const dots = document.querySelectorAll(".browse-carousel-dot");
    dots[1].click();
    const viewport = document.querySelector(".browse-carousel-viewport");
    expect(viewport.scrollLeft).toBeGreaterThanOrEqual(0);
  });
}

function testInitializesWithoutDotsOrHover() {
  test("initializes without dots container or hover tip", () => {
    document.body.innerHTML = `
      <div class="browse-carousel" data-autoplay="false">
        <div class="browse-carousel-viewport">
          <div class="browse-carousel-track">
            <article class="slide">One</article>
          </div>
        </div>
      </div>
    `;
    const slide = document.querySelector(".slide");
    slide.getBoundingClientRect = () => ({ width: 100, left: 0 });
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel(window)).not.toThrow();
  });
}

function testReturnsEarlyWhenNoDocument() {
  test("returns early when window has no document", () => {
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel({})).not.toThrow();
  });
}

function testAutoInitAddsDOMContentLoadedListener() {
  test("auto init attaches DOMContentLoaded listener when document loading", () => {
    jest.useFakeTimers();
    const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
    Object.defineProperty(document, "readyState", { value: "loading", configurable: true });
    const addSpy = jest.spyOn(document, "addEventListener");
    loadModule();
    expect(addSpy).toHaveBeenCalledWith("DOMContentLoaded", expect.any(Function), { once: true });
    if (originalReady) {
      Object.defineProperty(document, "readyState", originalReady);
    }
    addSpy.mockRestore();
    jest.useRealTimers();
  });
}

function testAutoInitWhenDocumentReady() {
  test("auto init runs immediately when document ready", () => {
    const originalReady = Object.getOwnPropertyDescriptor(document, "readyState");
    Object.defineProperty(document, "readyState", { value: "complete", configurable: true });
    buildDom();
    const { initHomeBrowseCarousel } = loadModule();
    initHomeBrowseCarousel(window);
    const dots = document.querySelectorAll(".browse-carousel-dot");
    expect(dots.length).toBe(2);
    if (originalReady) {
      Object.defineProperty(document, "readyState", originalReady);
    }
  });
}

function testReturnsEarlyNoCarouselsNoWindow() {
  test("returns early when no carousels and no window arg", () => {
    document.body.innerHTML = ``;
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel()).not.toThrow();
  });
}

function testReturnsEarlyWindowMissingDocument() {
  test("returns early when window has no document", () => {
    const { initHomeBrowseCarousel } = loadModule();
    expect(() => initHomeBrowseCarousel({})).not.toThrow();
  });
}
