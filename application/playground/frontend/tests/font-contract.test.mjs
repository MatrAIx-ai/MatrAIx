import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("Inter is the only configured text face", async () => {
  const [html, tailwind, css, design] = await Promise.all([
    read("index.html"),
    read("tailwind.config.ts"),
    read("src/index.css"),
    read("DESIGN.md"),
  ]);
  const textConfiguration = [html, tailwind, css, design].join("\n");

  assert.doesNotMatch(textConfiguration, /Space Grotesk|JetBrains Mono/);
  assert.match(html, /family=Inter:wght@400;500;600;700/);
  assert.match(html, /family=Material\+Symbols\+Outlined/);
  assert.match(tailwind, /const interFontFamily = \["Inter", "system-ui", "sans-serif"\]/);
  assert.match(tailwind, /sans: interFontFamily/);
  assert.match(tailwind, /display: interFontFamily/);
  assert.match(tailwind, /mono: interFontFamily/);
  assert.match(css, /--sans: "Inter"/);
  assert.match(css, /--display: var\(--sans\)/);
  assert.match(css, /--mono: var\(--sans\)/);
});
