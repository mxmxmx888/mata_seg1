if (typeof global.FileList === "undefined") {
  global.FileList = class {};
}

const { setInputFiles, getFiles } = require("../../static/js/create_recipe_helpers");

describe("create_recipe_helpers setInputFiles", () => {
  let originalDT;

  beforeEach(() => {
    originalDT = global.DataTransfer;
  });

  afterEach(() => {
    global.DataTransfer = originalDT;
  });

  test("uses native file setter when available", () => {
    delete global.DataTransfer;
    const input = {};
    let assigned = null;
    Object.defineProperty(input, "files", {
      configurable: true,
      set: (val) => {
        assigned = val;
      },
      get: () => assigned,
    });
    const files = ["file"];

    setInputFiles(input, files);

    expect(assigned).toBe(getFiles(input));
    expect(getFiles(input).length).toBe(files.length);
  });

  test("falls back to defining getter when native setter fails", () => {
    delete global.DataTransfer;
    const input = {};
    Object.defineProperty(input, "files", {
      configurable: true,
      set: () => {
        throw new Error("no setter");
      },
      get: () => null,
    });
    const files = ["file"];

    setInputFiles(input, files);

    expect(getFiles(input)).toBe(files);
  });

  test("normalizes arrays to a FileList via DataTransfer when available", () => {
    const fileObj = { name: "photo.png" };
    const added = [];
    const fakeFiles = { length: 1 };
    global.DataTransfer = class {
      constructor() {
        this.items = {
          add: (f) => added.push(f),
        };
        this.files = fakeFiles;
      }
    };

    const input = {};
    let assigned = null;
    Object.defineProperty(input, "files", {
      configurable: true,
      set: (val) => {
        assigned = val;
      },
      get: () => assigned,
    });

    setInputFiles(input, [fileObj]);

    expect(added).toContain(fileObj);
    expect(assigned).toBe(fakeFiles);
    expect(getFiles(input)).toBe(fakeFiles);
  });

  test("assigns files directly when no descriptor is present", () => {
    delete global.DataTransfer;
    const input = {};
    const files = [{ name: "a" }];

    setInputFiles(input, files);

    expect(input.files).toBe(files);
    expect(getFiles(input)).toBe(files);
  });
});
