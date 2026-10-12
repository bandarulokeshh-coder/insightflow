/**
 * Runtime page verification.
 *
 * Loads every route in a real browser and fails if it finds:
 *   · hydration errors (they are logged to the console, not the terminal)
 *   · console errors or uncaught page errors
 *   · Next's dev error overlay
 *
 * Why this exists: a green `next build` does NOT prove the UI works. Two real
 * bugs shipped past the build in this project — Tailwind never emitting
 * utilities, and a stale .next producing hydration mismatches — and only a
 * rendered page caught them.
 *
 * Requires the dev server on :3000 and playwright installed:
 *   npx playwright install chromium
 *   npm run verify
 */
import { chromium } from "playwright";

const BASE = process.env.BASE_URL || "http://localhost:3000";
const ROUTES = ["/", "/feedback", "/refinery", "/recommendations", "/issues", "/reports"];

const browser = await chromium.launch();
let failures = 0;

for (const route of ROUTES) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const problems = [];

  page.on("console", (m) => {
    if (m.type() === "error") problems.push(`console.error: ${m.text().slice(0, 140)}`);
  });
  page.on("pageerror", (e) => problems.push(`pageerror: ${String(e).slice(0, 140)}`));

  try {
    await page.goto(`${BASE}${route}`, { waitUntil: "networkidle", timeout: 45000 });
    await page.waitForTimeout(2000);

    const portalText = await page.locator("nextjs-portal").first().innerText().catch(() => "");
    const hasErrorOverlay = /hydration|unhandled|recoverable|uncaught|failed to compile/i.test(portalText);
    const dialogs = await page.locator("[data-nextjs-dialog], [data-nextjs-error-overlay]").count();
    const heading = ((await page.locator("h1").first().textContent().catch(() => "")) || "").trim();

    // Tailwind must actually be emitting utilities — a silent failure mode
    const flexGap = await page.evaluate(() => {
      const el = document.querySelector(".panel");
      return el ? getComputedStyle(el).borderRadius : "";
    });
    const styled = flexGap !== "" && flexGap !== "0px";

    const bad = problems.length + (hasErrorOverlay ? 1 : 0) + dialogs + (styled ? 0 : 1);
    failures += bad;

    console.log(
      `${bad === 0 ? "PASS" : "FAIL"}  ${route.padEnd(18)} h1="${heading.slice(0, 22)}"` +
        ` tailwind=${styled ? "ok" : "MISSING"} overlay=${dialogs} errors=${problems.length}`
    );
    problems.slice(0, 3).forEach((p) => console.log(`        ${p}`));
  } catch (err) {
    failures += 1;
    console.log(`FAIL  ${route.padEnd(18)} navigation error: ${String(err).slice(0, 120)}`);
  } finally {
    await page.close();
  }
}

await browser.close();

if (failures === 0) {
  console.log("\nAll routes rendered cleanly: styles applied, no hydration or console errors.");
  process.exit(0);
}
console.log(`\n${failures} problem(s) found.`);
process.exit(1);
