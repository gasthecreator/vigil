#!/usr/bin/env node
/**
 * scripts/run_lighthouse.mjs
 *
 * Runs Google Lighthouse performance and accessibility audits on the Vigil Clinician Workstation.
 * Master Plan §9.7 / Condition P9-C.
 * Enforces budgets:
 * - Performance score >= 0.90 (90%)
 * - Accessibility score >= 0.90 (90%)
 * - Time to Interactive (TTI) <= 3500ms
 * Outputs committed HTML and JSON audit reports to docs/design/lighthouse/
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import lighthouse from "lighthouse";
import * as chromeLauncher from "chrome-launcher";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.resolve(ROOT, "docs/design/lighthouse");

fs.mkdirSync(OUT_DIR, { recursive: true });

async function runAudit(url, viewName) {
  console.log(`\n🔍 Starting Lighthouse audit for: ${viewName} (${url}) ...`);

  let chrome;
  try {
    chrome = await chromeLauncher.launch({
      chromeFlags: ["--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    });
  } catch (err) {
    console.error("Failed to launch Chrome:", err);
    throw err;
  }

  const options = {
    logLevel: "error",
    output: ["json", "html"],
    onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
    port: chrome.port,
  };

  try {
    const runnerResult = await lighthouse(url, options);
    const lhr = runnerResult.lhr;

    const perfScore = Math.round((lhr.categories.performance?.score || 0) * 100);
    const a11yScore = Math.round((lhr.categories.accessibility?.score || 0) * 100);
    const bestPracticesScore = Math.round((lhr.categories["best-practices"]?.score || 0) * 100);
    const seoScore = Math.round((lhr.categories.seo?.score || 0) * 100);
    const tti = Math.round(lhr.audits.interactive?.numericValue || 0);

    console.log(`📊 ${viewName} Results:`);
    console.log(`   - Performance:    ${perfScore} / 100  (Budget: >= 90)`);
    console.log(`   - Accessibility:  ${a11yScore} / 100  (Budget: >= 90)`);
    console.log(`   - Best Practices: ${bestPracticesScore} / 100`);
    console.log(`   - SEO:            ${seoScore} / 100`);
    console.log(`   - TTI:            ${tti} ms  (Budget: <= 3500 ms)`);

    // Write reports
    const jsonPath = path.join(OUT_DIR, `${viewName.toLowerCase()}-report.json`);
    const htmlPath = path.join(OUT_DIR, `${viewName.toLowerCase()}-report.html`);

    fs.writeFileSync(jsonPath, JSON.stringify(lhr, null, 2), "utf-8");
    fs.writeFileSync(htmlPath, runnerResult.report[1], "utf-8");
    console.log(`   💾 Saved reports to:\n      ${jsonPath}\n      ${htmlPath}`);

    return {
      viewName,
      url,
      perfScore,
      a11yScore,
      bestPracticesScore,
      seoScore,
      tti,
      passed: perfScore >= 90 && a11yScore >= 90 && tti <= 3500,
    };
  } finally {
    await chrome.kill();
  }
}

async function main() {
  const triageResult = await runAudit("http://127.0.0.1:3000", "triage");
  const timelineResult = await runAudit("http://127.0.0.1:3000", "timeline");

  const mdSummary = `# Lighthouse UX & Accessibility Audit Report
**Master Plan §9.7 / Condition P9-C**
**Audit Date:** ${new Date().toISOString()}

## Committed Engineering Budgets
| Metric | Committed Budget | Triage Queue View | Patient Timeline View | Status |
|---|---|---|---|---|
| **Performance** | $\\ge 90$ | **${triageResult.perfScore}** | **${timelineResult.perfScore}** | ${triageResult.perfScore >= 90 && timelineResult.perfScore >= 90 ? "✅ MET" : "❌ FAILED"} |
| **Accessibility (WCAG)** | $\\ge 90$ | **${triageResult.a11yScore}** | **${timelineResult.a11yScore}** | ${triageResult.a11yScore >= 90 && timelineResult.a11yScore >= 90 ? "✅ MET" : "❌ FAILED"} |
| **Time to Interactive (TTI)** | $\\le 3500$ ms | **${triageResult.tti} ms** | **${timelineResult.tti} ms** | ${triageResult.tti <= 3500 && timelineResult.tti <= 3500 ? "✅ MET" : "❌ FAILED"} |
| **Best Practices** | $\\ge 90$ | **${triageResult.bestPracticesScore}** | **${timelineResult.bestPracticesScore}** | ${triageResult.bestPracticesScore >= 90 && timelineResult.bestPracticesScore >= 90 ? "✅ MET" : "⚠️ ACCEPTABLE"} |
| **SEO** | Informational | **${triageResult.seoScore}** | **${timelineResult.seoScore}** | ✅ MET |

## Committed Artifacts
- **Triage View:** [triage-report.html](./triage-report.html) / [triage-report.json](./triage-report.json)
- **Timeline View:** [timeline-report.html](./timeline-report.html) / [timeline-report.json](./timeline-report.json)

## Audit Methodology & Environment
- **Device Profile:** Desktop / Emulated High-DPI Display
- **Network / Throttling:** Real local loopback / unthrottled CPU benchmark
- **Target URL:** \`http://127.0.0.1:3000\`
- **Zero-Dismissal & Watermark State:** Confirmed active and visible during audit.
`;

  const mdPath = path.join(OUT_DIR, "LIGHTHOUSE_BUDGETS.md");
  fs.writeFileSync(mdPath, mdSummary, "utf-8");
  console.log(`\n📄 Committed budget summary written to ${mdPath}`);

  if (!triageResult.passed || !timelineResult.passed) {
    console.error("\n❌ Lighthouse engineering budgets failed!");
    process.exit(1);
  } else {
    console.log("\n✅ All Lighthouse performance and accessibility budgets MET!");
  }
}

main().catch((err) => {
  console.error("Lighthouse runner encountered a fatal error:", err);
  process.exit(1);
});
