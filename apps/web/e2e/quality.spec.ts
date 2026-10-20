import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as path from "path";

const SCREENS_DIR = path.resolve(__dirname, "../../../docs/design/screens");

test.describe("M10 Missed-Signal Quality Audit E2E Suite (Real Backend)", () => {
  test.beforeEach(async () => {
    // Real server: zero page.route fakes for /api/v1
  });

  test("Accessibility Audit: Quality Audit Workstation meets WCAG 2.2 AA (Zero serious/critical violations)", async ({
    page,
  }) => {
    await page.goto("/quality");
    await page.waitForSelector("header");
    await page.waitForSelector("table[aria-label='Subgroup Breakdown']", { timeout: 15000 });
    await expect(
      page
        .getByRole("status")
        .getByText("Synthetic benchmark only — these results are not facility data.")
    ).toBeVisible();

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    const seriousViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(seriousViolations).toEqual([]);
  });

  test("Quality Audit Workstation: Headers, Governance Policy, and KPI Overview", async ({
    page,
  }) => {
    await page.goto("/quality");
    await page.waitForSelector("header");

    // 1. Header & Governance Notice
    await expect(
      page.locator("h2:has-text('Surveillance Quality & Missed-Signal Audit')")
    ).toBeVisible();
    await expect(
      page.locator("text=ADR 0016 Institutional Privacy & Descriptive Register Policy")
    ).toBeVisible();
    await expect(page.locator("text=signal present, action not recorded")).toBeVisible();

    // 2. Audit Parameter Controls
    await expect(page.locator("label:has-text('Surveillance Lookback:')")).toBeVisible();
    await expect(page.locator("label:has-text('Bootstrap Resamples:')")).toBeVisible();
    await expect(page.locator("button:has-text('Run Retrospective Audit')")).toBeVisible();

    // 3. Summary Cards
    await expect(page.locator("text=Total Audited Cohort")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Signals Meeting Criteria")).toBeVisible();
    await expect(page.locator("text=Timely Action Recorded")).toBeVisible();
    await expect(page.locator("span:has-text('Action Not Recorded')")).toBeVisible();

    // 4. Neutral Narrative Summary Card
    await expect(page.locator("text=Verified Neutral Narrative")).toBeVisible();
    await expect(page.locator("text=Descriptive Register Verified")).toBeVisible();
  });

  test("Quality Audit Engine: Executes fresh audit, renders tabs, and verifies small-cell suppression (<5)", async ({
    page,
  }) => {
    await page.goto("/quality");
    await page.waitForSelector("header");
    await page.waitForSelector("table[aria-label='Subgroup Breakdown']", { timeout: 15000 });

    // Click Run Retrospective Audit
    await page.click("button:has-text('Run Retrospective Audit')");

    // Wait for audit completion and KPI visibility
    await expect(page.locator("text=Total Audited Cohort")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("span:has-text('Action Not Recorded')")).toBeVisible();

    // Tab navigation: Cancer Subtype
    await page.click("button:has-text('Cancer Subtype')");
    await expect(page.locator("table[aria-label='Subtype Breakdown']")).toBeVisible();

    // Tab navigation: Initial Stage
    await page.click("button:has-text('Initial Stage')");
    await expect(page.locator("table[aria-label='Stage Breakdown']")).toBeVisible();

    // Verify small-cell suppression badge
    await expect(page.locator("text=k ≥ 5 Suppressed").first()).toBeVisible();

    // Capture visual snapshot of the M10 Quality Audit Workstation
    await page.screenshot({
      path: path.join(SCREENS_DIR, "m10_quality_audit_workstation.png"),
      fullPage: true,
    });
  });
});
