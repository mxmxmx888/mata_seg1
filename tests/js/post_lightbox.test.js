const { initPostLightbox } = require("../../static/js/post_lightbox");

function buildLightboxDom() {
  document.body.innerHTML = `
    <div id="lightbox" class="d-none">
      <div class="lightbox-backdrop"></div>
      <button class="lightbox-arrow lightbox-arrow--left" type="button"></button>
      <img id="lightbox-image" class="lightbox-image" alt="Recipe image">
      <button class="lightbox-arrow lightbox-arrow--right" type="button"></button>
    </div>
    <img class="js-gallery-image" src="thumb1.jpg" data-fullsrc="full1.jpg">
    <img class="js-gallery-image" src="thumb2.jpg" data-fullsrc="full2.jpg">
  `;
}

describe("post_lightbox", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  test("opens lightbox on thumb click and navigates images", () => {
    buildLightboxDom();
    initPostLightbox(window);
    const thumbs = document.querySelectorAll(".js-gallery-image");
    const lightbox = document.getElementById("lightbox");
    const img = document.getElementById("lightbox-image");

    thumbs[0].dispatchEvent(new Event("click", { bubbles: true }));
    expect(lightbox.classList.contains("d-none")).toBe(false);
    expect(img.src).toContain("full1.jpg");

    document.querySelector(".lightbox-arrow--right").click();
    expect(img.src).toContain("full2.jpg");

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
    expect(img.src).toContain("full1.jpg");
  });

  test("closes on escape and backdrop", () => {
    buildLightboxDom();
    initPostLightbox(window);
    const lightbox = document.getElementById("lightbox");
    const backdrop = lightbox.querySelector(".lightbox-backdrop");
    document.querySelector(".js-gallery-image").click();
    backdrop.click();
    expect(lightbox.classList.contains("d-none")).toBe(true);

    document.querySelector(".js-gallery-image").click();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(lightbox.classList.contains("d-none")).toBe(true);
  });

  test("ignores key events when closed and exits when no thumbs", () => {
    document.body.innerHTML = `<div id="lightbox"><div class="lightbox-backdrop"></div><button class="lightbox-arrow lightbox-arrow--left"></button><img id="lightbox-image"><button class="lightbox-arrow lightbox-arrow--right"></button></div>`;
    initPostLightbox(window);
    expect(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }))).not.toThrow();

    buildLightboxDom();
    initPostLightbox(window);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
    // still closed so img source not set
    expect(document.getElementById("lightbox-image").src).not.toContain("full1.jpg");
  });

  test("advances with ArrowRight while open", () => {
    buildLightboxDom();
    initPostLightbox(window);
    document.querySelector(".js-gallery-image").click();
    const img = document.getElementById("lightbox-image");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    expect(img.src).toContain("full2.jpg");
  });

  test("early exit when no thumbs or lightbox elements", () => {
    document.body.innerHTML = `<div></div>`;
    expect(() => initPostLightbox(window)).not.toThrow();
  });

  test("wraps to last image when navigating left from first", () => {
    buildLightboxDom();
    initPostLightbox(window);
    document.querySelectorAll(".js-gallery-image")[0].click();
    const img = document.getElementById("lightbox-image");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
    expect(img.src).toContain("full2.jpg");
  });

  test("falls back to thumb src when fullsrc missing", () => {
    document.body.innerHTML = `
      <div id="lightbox" class="d-none">
        <div class="lightbox-backdrop"></div>
        <button class="lightbox-arrow lightbox-arrow--left" type="button"></button>
        <img id="lightbox-image" class="lightbox-image" alt="Recipe image">
        <button class="lightbox-arrow lightbox-arrow--right" type="button"></button>
      </div>
      <img class="js-gallery-image" src="thumb-only.jpg">
    `;
    initPostLightbox(window);
    document.querySelector(".js-gallery-image").click();
    expect(document.getElementById("lightbox-image").src).toContain("thumb-only.jpg");
  });

  test("returns early when window lacks document", () => {
    expect(() => initPostLightbox({})).not.toThrow();
  });

  test("ignores unrelated key presses while open", () => {
    buildLightboxDom();
    initPostLightbox(window);
    document.querySelector(".js-gallery-image").click();
    const img = document.getElementById("lightbox-image");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(img.src).toContain("full1.jpg");
  });
});
