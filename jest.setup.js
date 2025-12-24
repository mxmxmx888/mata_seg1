// Lightweight mocks for browser APIs used in tests.
const defaultMatchMedia = (query) => ({
  matches: false,
  media: query,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  addListener: jest.fn(),
  removeListener: jest.fn(),
  onchange: null
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation(defaultMatchMedia)
});

// JSDOM lacks DataTransfer; provide a minimal stub if a test needs it later.
if (typeof window.DataTransfer === "undefined") {
  window.DataTransfer = class DataTransfer {
    constructor() {
      this._files = [];
      this.items = {
        add: (file) => {
          this._files.push(file);
        }
      };
    }

    get files() {
      return this._files;
    }
  };
}
