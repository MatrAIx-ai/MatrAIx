import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shots = path.resolve(
  here,
  "../../../../docs/superpowers/specs/assets/2026-07-12-synthesis-adjust-generate",
);
const shotNames = ["1-adjust-generate.png", "2-distribution.png", "3-overlay.png"] as const;

async function settleForScreenshot(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
  });
}

test("pin, scale, generate, compare, render, overlay, and preserve results on error", async ({
  page,
}) => {
  mkdirSync(shots, { recursive: true });
  for (const shotName of shotNames) rmSync(path.join(shots, shotName), { force: true });

  const pageErrors: string[] = [];
  const consoleIssues: { type: string; text: string }[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.stack ?? error.message));
  page.on("console", (message) => {
    if (message.type() === "warning" || message.type() === "error") {
      consoleIssues.push({ type: message.type(), text: message.text() });
    }
  });

  await page.goto("/?view=synthesis");
  expect(page.url()).toBe("http://127.0.0.1:8766/?view=synthesis");
  expect(await page.title()).toBe("MatrAIx — simulate users across your applications");
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toHaveText("Persona DAG Studio");

  const overviewGraph = page.getByRole("group", { name: "Persona DAG category overview" });
  await expect(overviewGraph).toBeVisible();
  await expect(
    page.getByText(/^\d[\d,]* nodes · \d[\d,]* directed edges · \d+ categories$/),
  ).toBeVisible();
  const frameworkOverlays = page.locator(
    "vite-error-overlay, nextjs-portal, [data-nextjs-dialog-overlay], [data-webpack-error-overlay]",
  );
  await expect(frameworkOverlays).toHaveCount(0);

  const demographicCategory = page.getByRole("button", { name: /^Demographic: Core —/ });
  await demographicCategory.focus();
  await demographicCategory.press("Enter");
  await expect(demographicCategory).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: /^Region\b/ }).click();
  await page.getByRole("button", { name: "Pin Region to North America" }).click();
  await page.getByRole("button", { name: /back to category list/i }).click();

  await page.getByRole("button", { name: /^Age bracket\b/ }).click();
  await page.getByRole("button", { name: "Pin Age bracket to 25-34" }).click();
  await page.getByRole("button", { name: /back to category list/i }).click();
  await page.getByRole("button", { name: "Influence ×" }).click();
  const influence = page.getByRole("slider", {
    name: "Influence of Demographic: Core",
  });
  await influence.focus();
  await influence.press("Home");
  for (let step = 0; step < 20; step += 1) await influence.press("ArrowRight");
  const categoryRecipe = page
    .getByTestId("synthesis-recipe-entry")
    .filter({ hasText: "Demographic: Core" });
  await expect(categoryRecipe).toContainText("2.0×");

  await page.getByRole("spinbutton", { name: "Personas" }).fill("50");
  const generate = page.getByRole("button", { name: "Generate" });
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/synthesis/sample" &&
        response.status() === 200,
    ),
    generate.click(),
  ]);
  const personasTab = page.getByRole("tab", { name: "Personas (50)" });
  await expect(personasTab).toBeVisible();
  await expect(page.getByText("1–10 of 50", { exact: true })).toBeVisible();
  const adjustGenerateGlassPanel = page
    .getByText("Adjust & Generate", { exact: true })
    .locator("..")
    .locator("..");
  await adjustGenerateGlassPanel.scrollIntoViewIfNeeded();
  await settleForScreenshot(page);
  await adjustGenerateGlassPanel.screenshot({ path: path.join(shots, shotNames[0]) });

  const pageRanges = [
    "1–10 of 50",
    "11–20 of 50",
    "21–30 of 50",
    "31–40 of 50",
    "41–50 of 50",
  ];
  for (let resultPage = 0; resultPage < pageRanges.length; resultPage += 1) {
    await expect(page.getByText(pageRanges[resultPage], { exact: true })).toBeVisible();
    const cards = page.getByTestId("synthesis-persona-card");
    await expect(cards).toHaveCount(10);
    for (let cardIndex = 0; cardIndex < 10; cardIndex += 1) {
      const card = cards.nth(cardIndex);
      await card.scrollIntoViewIfNeeded();
      await expect(card.getByTitle("North America", { exact: true })).toBeVisible();
      await expect(card.getByTitle("25-34", { exact: true })).toBeVisible();
    }
    if (resultPage < pageRanges.length - 1) {
      await page.getByRole("button", { name: "Next" }).click();
    }
  }

  await page.getByRole("tab", { name: "Distribution" }).click();
  const distributionSurface = page.getByRole("tabpanel", { name: "Distribution" });
  const tvdLabels = page.getByText(/^TVD [01]\.\d{3}$/);
  await expect(tvdLabels.first()).toBeVisible();
  const tvds = await tvdLabels.allTextContents();
  const values = tvds.map((text) => Number(text.replace("TVD ", "")));
  expect(values.length).toBeGreaterThan(0);
  expect(values).toEqual([...values].sort((left, right) => right - left));
  await distributionSurface.scrollIntoViewIfNeeded();
  await settleForScreenshot(page);
  const resultsGlassPanel = page
    .getByText("Results", { exact: true })
    .locator("..")
    .locator("..");
  await resultsGlassPanel.screenshot({ path: path.join(shots, shotNames[1]) });

  await personasTab.click();
  for (let pageIndex = 0; pageIndex < 4; pageIndex += 1) {
    await page.getByRole("button", { name: "Previous" }).click();
  }
  await expect(page.getByText("1–10 of 50", { exact: true })).toBeVisible();
  const firstCard = page.getByTestId("synthesis-persona-card").first();
  await firstCard.scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Remove pin on Region" }).click();
  await firstCard.scrollIntoViewIfNeeded();
  await expect(firstCard.getByText("Pinned.")).toHaveCount(2);
  await expect(firstCard.getByTitle("North America", { exact: true })).toBeVisible();
  await expect(firstCard.getByTitle("25-34", { exact: true })).toBeVisible();
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/synthesis/render" &&
        response.status() === 200,
    ),
    firstCard.getByRole("button", { name: "Text", exact: true }).click(),
  ]);
  await expect(firstCard.getByText(/^A persona /)).toBeVisible();
  await firstCard.getByRole("button", { name: "Overlay", exact: true }).click();
  await expect(
    firstCard.getByRole("button", { name: "Overlaying", exact: true }),
  ).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  const ageOverlay = page.getByRole("button", {
    name: /Age bracket.*sampled value 25-34/,
  });
  await ageOverlay.scrollIntoViewIfNeeded();
  await expect(ageOverlay).toBeVisible();

  const categoryTitleBar = page.getByText("Category overview", { exact: true }).locator("..");
  await categoryTitleBar.getByRole("button", { name: "Expand panel" }).click();
  await expect(categoryTitleBar.getByRole("button", { name: "Restore panel" })).toBeVisible();
  const demographicOverlay = page.getByRole("button", {
    name: /^Demographic: Core — .* · 25 sampled values: .* · contains pinned attributes$/,
  });
  await demographicOverlay.scrollIntoViewIfNeeded();
  await expect(demographicOverlay).toBeInViewport();
  await expect(demographicOverlay.locator("circle")).toHaveCount(3);
  await expect(demographicOverlay.locator("circle").last()).toHaveAttribute(
    "style",
    /var\(--warn\)/,
  );
  await overviewGraph.scrollIntoViewIfNeeded();
  await settleForScreenshot(page);
  await categoryTitleBar
    .locator("..")
    .screenshot({ path: path.join(shots, shotNames[2]) });

  await page.route("**/api/synthesis/sample", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "sampling temporarily unavailable" }),
    });
  });
  await Promise.all([
    page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/synthesis/sample" &&
        response.status() === 503,
    ),
    generate.click(),
  ]);
  await expect(page.getByRole("alert")).toContainText("sampling temporarily unavailable");
  await expect(personasTab).toBeVisible();
  await expect(page.getByText("1–10 of 50", { exact: true })).toBeVisible();
  await firstCard.scrollIntoViewIfNeeded();
  await expect(firstCard.getByTitle("North America", { exact: true })).toBeVisible();
  await expect(
    firstCard.getByRole("button", { name: "Overlaying", exact: true }),
  ).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(demographicOverlay).toHaveCount(1);

  await page.unroute("**/api/synthesis/sample");
  await page.route("**/api/synthesis/sample", async (route) => {
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        message: "unknown category: Demographic: Core",
        key: "overrides.categoryScales.Demographic: Core",
      }),
    });
  });
  await Promise.all([
    page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/synthesis/sample" &&
        response.status() === 422,
    ),
    generate.click(),
  ]);
  await expect(page.getByRole("alert")).toContainText("unknown category");
  await expect(categoryRecipe).toHaveAttribute("data-invalid", "true");

  await page.unroute("**/api/synthesis/sample");
  await page.getByRole("spinbutton", { name: "Personas" }).fill("0");
  await expect(
    page.getByText("Personas must be an integer between 1 and 200.", { exact: true }),
  ).toBeVisible();
  await expect(generate).toBeDisabled();

  await expect(frameworkOverlays).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  const expectedFailure =
    /^Failed to load resource: the server responded with a status of (422|503) \([^)]*\)$/;
  const unexpectedConsoleIssues = consoleIssues.filter(
    (issue) => issue.type !== "error" || !expectedFailure.test(issue.text),
  );
  expect(unexpectedConsoleIssues).toEqual([]);
});
