const fs = require("fs");
const path = require("path");

const templatesRoot = path.join(__dirname, "..", "..", "recipes", "templates");

function collectHtmlFiles(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .flatMap((entry) => {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        return collectHtmlFiles(fullPath);
      }
      return entry.isFile() && entry.name.endsWith(".html") ? [fullPath] : [];
    });
}

function lineNumber(content, index) {
  return content.slice(0, index).split(/\n/).length;
}

describe("Templates", () => {
  it("do not include inline style tags or attributes", () => {
    const files = collectHtmlFiles(templatesRoot);
    const offenders = [];
    files.forEach((filePath) => {
      const content = fs.readFileSync(filePath, "utf8");
      const relPath = path.relative(path.join(__dirname, "..", ".."), filePath);
      [...content.matchAll(/<style[\s>]/gi)].forEach((match) => {
        offenders.push(`${relPath}:${lineNumber(content, match.index)} contains <style> tag`);
      });
      [...content.matchAll(/style\s*=\s*["']/gi)].forEach((match) => {
        offenders.push(`${relPath}:${lineNumber(content, match.index)} has inline style attribute`);
      });
    });
    expect(offenders).toEqual([]);
  });
});
