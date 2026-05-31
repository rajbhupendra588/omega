import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.join(root, "docs", "screenshots");
const baseUrl = "http://127.0.0.1:8765";

const shots = [
  { name: "dashboard", url: `${baseUrl}/`, waitMs: 2000 },
  { name: "new-analysis", url: `${baseUrl}/analyze`, waitMs: 1000 },
  { name: "report-overview", url: `${baseUrl}/reports/d5349ef7d1fd`, waitMs: 2500 },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await mkdir(outDir, { recursive: true });

for (const shot of shots) {
  await page.goto(shot.url, { waitUntil: "networkidle" });
  await page.waitForTimeout(shot.waitMs);
  await page.screenshot({
    path: path.join(outDir, `${shot.name}.png`),
    fullPage: true,
  });
}

await page.goto(`${baseUrl}/reports/d5349ef7d1fd`, { waitUntil: "networkidle" });
await page.waitForTimeout(2000);
await page.getByRole("button", { name: /Improvements/ }).click();
await page.waitForTimeout(500);
await page.screenshot({
  path: path.join(outDir, "report-improvements.png"),
  fullPage: false,
});

await browser.close();
console.log(`Saved screenshots to ${outDir}`);
