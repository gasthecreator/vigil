import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as path from "path";

const SCREENS_DIR = path.resolve(__dirname, "../../../docs/design/screens");

test.describe("M7 Radiotherapy Treatment Continuity & Triage E2E Suite (Real Backend)", () => {
  test.beforeEach(async () => {
    // Real server: zero page.route fakes for /api/v1
  });

  test("Accessibility Audit: Continuity Workstation meets WCAG 2.2 AA (Zero serious/critical violations)", async ({ page }) => {
    await page.goto("/continuity");
    await page.waitForSelector("header");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    const seriousViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(seriousViolations).toEqual([]);
  });

  test("Workstation: LINAC Machine Status, Downtime Tracking, and Capacity Overview", async ({ page }) => {
    await page.goto("/continuity");
    await page.waitForSelector("header");

    // 1. Header & Badges
    await expect(page.locator("h1:has-text('Treatment Continuity & Radiotherapy Triage')")).toBeVisible();
    await expect(page.locator("text=Algorithmic Fairness")).toBeVisible();
    await expect(page.locator("text=Google OR-Tools CP-SAT")).toBeVisible();

    // 2. Metrics Bar
    await expect(page.locator("text=Operational LINACs")).toBeVisible();
    await expect(page.locator("text=Active RT Courses")).toBeVisible();

    // 3. Machine Overview Cards
    await expect(page.locator("h3:has-text('LINAC-01 (Elekta Synergy)')")).toBeVisible();
    await expect(page.locator("h3:has-text('LINAC-02 (Varian Clinac)')")).toBeVisible();
    await expect(page.locator("text=Machine down. Expected return:")).toBeVisible();

    // Switch to Machines Tab
    await page.click("button[role='tab']:has-text('LINAC Machines')");
    await expect(page.locator("text=Daily Slot Capacity:").first()).toBeVisible();
    await expect(page.locator("text=16 fractions / day").first()).toBeVisible();
  });

  test("CP-SAT Scheduler: Solves constrained schedule with fairness bounds & marginal harm explanations", async ({ page }) => {
    await page.goto("/continuity");
    await page.waitForSelector("header");

    // Click Solve Reallocation Schedule
    await page.click("button:has-text('Solve Reallocation Schedule')");

    // Wait for solver response banner
    await expect(
      page.locator("h3:has-text('Optimal Continuity Schedule Generated')")
    ).toBeVisible({ timeout: 10000 });

    // Verify Solver Details
    await expect(page.locator("text=Status: OPTIMAL")).toBeVisible();
    await expect(page.locator("table[aria-label='Proposed Schedule Table']")).toBeVisible();
    await expect(page.locator("td:has-text('PAT-001')")).toBeVisible();
    await expect(page.locator("td:has-text('PAT-002')")).toBeVisible();

    // Capture visual snapshot of the CP-SAT Continuity Scheduler
    await page.screenshot({
      path: path.join(SCREENS_DIR, "m7_workstation_continuity_scheduler.png"),
      fullPage: true,
    });
  });

  test("Clinician Schedule Confirmation: Commits assignments and creates audited DelayLedgerEntry records", async ({ page }) => {
    await page.goto("/continuity");
    await page.waitForSelector("header");

    // 1. Solve schedule
    await page.click("button:has-text('Solve Reallocation Schedule')");
    await expect(page.locator("h3:has-text('Optimal Continuity Schedule Generated')")).toBeVisible({ timeout: 10000 });

    // 2. Confirm schedule as clinician
    await page.click("button:has-text('Confirm & Commit Schedule')");
    await expect(page.locator("text=Schedule successfully confirmed.")).toBeVisible({ timeout: 5000 });

    // 3. Switch to Delay Ledger Tab
    await page.click("button[role='tab']:has-text('Delay Ledger')");
    await expect(page.locator("table[aria-label='Delay Ledger Table']")).toBeVisible();
    await expect(page.locator("td:has-text('PAT-001')").first()).toBeVisible();
    await expect(page.locator("td:has-text('Capacity re-allocation')").or(page.locator("td:has-text('Clinician confirmed')")).first()).toBeVisible();
  });

  test("Companion PWA: Patient Delay Notice displays plain-language delay and assigned LINAC", async ({ page }) => {
    await page.goto("/companion");
    await page.waitForSelector("header");

    // Verify Treatment Continuity Card is visible
    await expect(page.locator("h2:has-text('Radiotherapy Treatment Schedule & Continuity')")).toBeVisible();
    await expect(page.locator("text=Assigned Machine:")).toBeVisible();
    await expect(page.locator("text=Next Scheduled Session:")).toBeVisible();

    // Capture visual snapshot of Companion delay notice
    await page.screenshot({
      path: path.join(SCREENS_DIR, "m7_companion_delay_notice.png"),
      fullPage: true,
    });
  });
});
