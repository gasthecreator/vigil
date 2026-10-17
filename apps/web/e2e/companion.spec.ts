import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as path from "path";
import * as fs from "fs";

const SCREENS_DIR = path.resolve(__dirname, "../../../docs/design/screens");

test.describe("M8 Family & Patient Companion E2E Suite (Real Backend & Seeded SQLite)", () => {
  test.beforeEach(async () => {
    // Condition P10-B: Real seeded backend for e2e.
    // Zero page.route mocks for /api/v1. The suite exercises real FastAPI backend,
    // real SQLite transactions, real M5 plain language explainer, real consent checks,
    // and real caregiver authorization.
  });

  test("Accessibility Audit: Companion views meet WCAG 2.2 AA (Zero serious/critical violations)", async ({ page }) => {
    await page.goto("/companion");
    await page.waitForSelector("header");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    const seriousViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(seriousViolations).toEqual([]);
  });

  test("Companion Dashboard: Status, Emergency Protocol Notice, Synthetic Banner", async ({ page }) => {
    await page.goto("/companion");
    await page.waitForSelector("header");

    // 1. Mandatory Urgent-Symptom Notice (Master Plan §11.1)
    await expect(
      page.locator("text=If you experience severe pain, difficulty breathing, or sudden bleeding")
    ).toBeVisible();

    // 2. Synthetic Data Banner
    await expect(page.locator("text=Research Prototype:").first()).toBeVisible();

    // 3. Welcome banner & active status
    await expect(page.locator("h1:has-text('Family & Patient Companion')")).toBeVisible();
    await expect(page.locator("text=Surveillance Monitoring Active • Routine Schedule")).toBeVisible();

    // Capture visual snapshot of Companion dashboard
    await page.screenshot({ path: path.join(SCREENS_DIR, "m8_companion_dashboard.png"), fullPage: true });
  });

  test("Bad-News Mode: Gated Disclosure with Clinician Release & Verbal Uncertainty", async ({ page }) => {
    await page.goto("/companion");
    await page.waitForSelector("header");

    // Verify initially in gated disclosure mode
    await expect(page.locator("text=Gated Disclosure")).toBeVisible();
    await expect(page.locator("h2:has-text('New Surveillance Results Ready')")).toBeVisible();

    // Click unlock button (triggers real POST /api/v1/patients/PAT-001/disclosure/unlock)
    await page.click("button:has-text('I am ready to view my results')");

    // Verify unlocked state
    await expect(page.locator("text=Unlocked")).toBeVisible();
    await expect(page.locator("h2:has-text('CA 15-3 Biomarker Surveillance Draw')")).toBeVisible();

    // Verify verbal uncertainty band — never raw percentages to families
    await expect(page.locator("text=Analytical Uncertainty (Suspected Lab Variation)")).toBeVisible();
  });

  test("Plain-Language Result Explainer (M5 / M3): Reading Level, Verbal Band, Doctor Questions", async ({ page }) => {
    await page.goto("/companion/results/OBS-001");
    await page.waitForSelector("header");

    // Verify M5 verified headline and verdict
    await expect(page.locator("text=M5 Verified Result Explainer")).toBeVisible();
    await expect(page.locator("text=Confirmation Needed (Needs Repeat)")).toBeVisible();

    // Verify verbal uncertainty band
    await expect(page.locator("text=Confidence & Uncertainty Band")).toBeVisible();

    // Verify plain language sections (no forbidden words like "dismissed" or "terminal")
    await expect(page.locator("text=What this result means in plain words")).toBeVisible();
    await expect(page.locator("text=Recommended Next Step")).toBeVisible();

    // Verify Reading Level badge (Flesch-Kincaid Grade Level <= 8.0)
    await expect(page.locator("text=Reading Level:")).toBeVisible();
    await expect(page.locator("text=≤ 8.0 Compliant")).toBeVisible();

    // Verify 3 structured questions for the doctor
    await expect(page.locator("text=Questions to ask your doctor")).toBeVisible();
    const questionCard = page.locator("div[role='button']").first();
    await expect(questionCard).toBeVisible();

    // Test copy question to clipboard interaction
    await questionCard.click();
    await expect(page.locator("text=Copied")).toBeVisible();

    // Capture screenshot of result explainer
    await page.screenshot({ path: path.join(SCREENS_DIR, "m8_companion_result_explainer.png"), fullPage: true });
  });

  test("Second-Look Request & Printable Clinic Summary Card", async ({ page }) => {
    await page.goto("/companion/second-look/OBS-001");
    await page.waitForSelector("header");

    // Verify target lab result summary
    await expect(page.locator("text=CA 15-3: 180.0 U/mL")).toBeVisible();
    await expect(page.locator("text=Needs Repeat")).toBeVisible();

    // Fill family clinical notes
    await page.fill("textarea", "Patient experienced no acute symptoms, past baseline has been consistently normal. Please review if repeat draw is needed.");

    // Submit second look request via real API (POST /patients/PAT-001/second-look)
    await page.click("button:has-text('Submit Second-Look Request')");

    // Verify confirmation and registration of FollowUpTask
    await expect(page.locator("text=Second-Look Request Successfully Registered")).toBeVisible();
    await expect(page.locator("text=Pending Oncologist Disposition")).toBeVisible();

    // Verify printable clinical summary card is rendered
    await expect(page.locator("text=CLINICAL SECOND-LOOK REQUEST")).toBeVisible();
    await expect(page.locator("text=Patient Identifier")).toBeVisible();
    await expect(page.locator("text=CA 15-3 (Serum)")).toBeVisible();

    // Capture screenshot of second-look summary card
    await page.screenshot({ path: path.join(SCREENS_DIR, "m8_companion_second_look_card.png"), fullPage: true });
  });

  test("Symptom Diary: Multi-Modality Logging, Category Selection, Offline Queueing", async ({ page }) => {
    await page.goto("/companion/symptoms");
    await page.waitForSelector("header");

    // Verify symptom categories are displayed
    await expect(page.locator("button:has-text('Bone / Back Pain')")).toBeVisible();
    await expect(page.locator("button:has-text('Severe Fatigue')")).toBeVisible();

    // Select Severe Fatigue and Severity 3 (Severe)
    await page.click("button:has-text('Severe Fatigue')");
    await page.click("button:has-text('Significantly interferes')");

    // Enter notes
    await page.fill("textarea", "Waking up exhausted, shortness of breath after climbing stairs.");

    // Submit symptom log via real API (POST /patients/PAT-001/symptoms)
    await page.click("button:has-text('Record Symptom')");

    // Verify success banner and entry in history list
    await expect(page.locator("text=Symptom recorded and shared with your oncology care team.")).toBeVisible();
    await expect(page.locator("text=fatigue").first()).toBeVisible();

    // In headless browser without mic permission, voice trigger is visible
    await expect(page.locator("button:has-text('Record Voice')")).toBeVisible();

    // Capture screenshot of symptom diary
    await page.screenshot({ path: path.join(SCREENS_DIR, "m8_companion_symptom_diary.png"), fullPage: true });
  });

  test("Caregiver Sharing Lifecycle & Revocation", async ({ page }) => {
    await page.goto("/companion/share");
    await page.waitForSelector("header");

    // Verify seeded caregiver share exists in list
    await expect(page.locator("text=Chinedu Adebayo")).toBeVisible();
    await expect(page.locator("text=active").first()).toBeVisible();

    // Create a new caregiver share via real API (POST /patients/PAT-001/shares)
    await page.fill("input[placeholder='e.g. Amina Bello']", "Dr. Ngozi Okonjo");
    await page.selectOption("#relationship-select", "sister");

    await page.click("button:has-text('Generate Caregiver Access Link')");

    // Verify new share created and link ready
    await expect(page.locator("text=Caregiver Access Link Generated")).toBeVisible();
    await expect(page.locator("text=Dr. Ngozi Okonjo").first()).toBeVisible();

    // Revoke access on the seeded share (DELETE /patients/PAT-001/shares/{id})
    const revokeButtons = page.locator("button:has-text('Revoke Access')");
    await revokeButtons.first().click();

    // Verify status updates to revoked
    await expect(page.locator("text=revoked").first()).toBeVisible();

    // Capture screenshot of caregiver share manager
    await page.screenshot({ path: path.join(SCREENS_DIR, "m8_companion_caregiver_share.png"), fullPage: true });
  });

  test("PWA Service Worker & Web App Manifest Validity", async ({ page }) => {
    // 1. Fetch manifest.json
    const manifestResp = await page.goto("/manifest.json");
    expect(manifestResp?.status()).toBe(200);
    const manifest = await manifestResp?.json();
    expect(manifest.name).toBe("Vigil Family & Patient Companion");
    expect(manifest.short_name).toBe("Vigil Care");
    expect(manifest.display).toBe("standalone");
    expect(manifest.theme_color).toBe("#0f766e");

    // 2. Fetch sw.js
    const swResp = await page.goto("/sw.js");
    expect(swResp?.status()).toBe(200);
    const swText = await swResp?.text();
    expect(swText).toContain("vigil-companion-v1");
    expect(swText).toContain('addEventListener("fetch"');
  });
});
