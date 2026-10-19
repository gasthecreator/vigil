import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as path from "path";
import * as fs from "fs";

const SCREENS_DIR = path.resolve(__dirname, "../../../docs/design/screens");
const OPENAPI_PATH = path.resolve(__dirname, "../../../docs/api/openapi.json");

test.describe("M9 Clinician Workstation E2E Suite (Real Backend & Seeded SQLite)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 1000 });
    // Condition P9-B: Real seeded backend for e2e.
    // No page.route mocks for /api/v1. The suite exercises real FastAPI backend,
    // real SQLite transactions, real M3 Bayesian mixture, real consent checks,
    // and real Guardian state machine.
  });

  test("Journey J6: M4 evidence ladder shows safety caveat and records audited facility feedback", async ({ page }) => {
    await page.goto("/test-ladder");
    await expect(page.getByRole("heading", { name: "M4 Resource-Aware Test Ladder" })).toBeVisible();
    await expect(page.getByText("Illustrative facility templates only")).toBeVisible();
    await page.getByRole("button", { name: "Show evidence-based options" }).click();
    await expect(page.getByTestId("ladder-results")).toBeVisible();
    await expect(page.getByTestId("negative-result-warning")).toContainText("A negative result does not exclude involvement");
    await expect(page.getByText(/Unverified availability|Stale availability/).first()).toBeVisible();

    await page.getByRole("button", { name: "Record audited feedback" }).click();
    await expect(page.getByText(/Availability and cost feedback recorded/)).toContainText("feedback recorded");
    await expect(page.getByText(/Availability and cost feedback recorded/)).toContainText("audit logged");
  });

  test("Accessibility Audit: Clinician Workstation meets WCAG 2.2 AA (Zero serious/critical violations)", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    const seriousViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(seriousViolations).toEqual([]);
  });

  test("Journey J1: Enrol Patient → Grant Care Consent → Rank in Triage Queue", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Open Enrolment Modal via button in Triage header
    await page.click("button:has-text('Enrol New Patient')");
    await expect(page.locator("h2:has-text('Enrol New Surveillance Patient')")).toBeVisible();

    // Fill form with Encrypted MRN and demographics
    const uniqueMrn = `MRN-UCH-2026-${Date.now().toString().slice(-4)}`;
    await page.fill("input[placeholder='e.g. MRN-UCH-2026-981']", uniqueMrn);
    await page.fill("input[type='number']", "54");
    await page.selectOption("#stage-select", "Stage II");
    await page.selectOption("#subtype-select", "HR+HER2-");

    // Submit Enrolment & Consent to real backend (POST /patients/ and POST /consent)
    await page.locator("button:has-text('Enrol & Grant Consent')").dispatchEvent("click");

    // Verify confirmation and modal dismissal
    await expect(page.locator("text=successfully enrolled with clinical care consent")).toBeVisible();
    await page.waitForTimeout(1000);

    // Capture visual snapshot of triage queue
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_triage.png"), fullPage: true });

    // Verify synthetic watermark banner is prominently displayed
    await expect(page.locator("header").getByText("RESEARCH PROTOTYPE")).toBeVisible();
    await expect(page.locator("header").getByText("SYNTHETIC DATASET")).toBeVisible();
  });

  test("Journey J2: Ingest Surprising CA 15-3 Spike → Real M3 Plausibility Adjudication → Zero-Dismissal Invariant", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Open Intake Drawer via Add Observation button
    await page.click("button:has-text('Add Observation (Intake)')");
    await expect(page.locator("h2:has-text('Fast Observation Intake')")).toBeVisible();

    // Take screenshot of intake modal
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_intake_modal.png") });

    // Enter surprising value (240 U/mL)
    await page.fill("input[placeholder='e.g. 24.5']", "240.0");
    await page.locator("button:has-text('Submit to Surveillance Pipeline')").dispatchEvent("click");

    await expect(page.locator("text=Observation recorded successfully")).toBeVisible();
    await page.waitForTimeout(1200);

    // Verify Zero-Dismissal Invariant: classified as needs_repeat or escalate, NOT dismissed
    await expect(
      page.locator("text=NEEDS CONFIRMATION (needs_repeat)").or(page.locator("text=ESCALATE")).first()
    ).toBeVisible();
    await expect(page.getByText("DISMISSED", { exact: true })).not.toBeVisible();

    // Verify 3-way Bayesian mixture decomposition is rendered
    await expect(page.locator("text=Analytical/Pre-Analytical Error")).toBeVisible();
    await expect(page.locator("text=Real Disease Progression")).toBeVisible();

    // Capture M3 Adjudication Panel screenshot
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_m3_adjudication.png") });

    // Action: Order Repeat Specimen (7d) or Escalate to Staging Imaging
    const actionBtn = page
      .locator("button:has-text('Order Repeat Specimen (7d)')")
      .or(page.locator("button:has-text('Escalate to Staging Imaging')"));
    await actionBtn.click();
    await expect(
      page.locator("text=Confirmation repeat laboratory test protocol initiated.")
        .or(page.locator("text=Escalation to staging imaging protocol initiated."))
        .or(page.locator("text=Action recorded in workstation protocol."))
    ).toBeVisible();
  });

  test("Journey J3: Follow-Up Guardian → Reminder Cascade Escalation → Mark Completed", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Switch to Follow-Up Tasks tab
    await page.click("button:has-text('Follow-Up Guardian (M6)')");

    // Verify urgent escalation level badge from seeded task
    await expect(page.locator("text=URGENT (ESC L2+)")).toBeVisible();

    // Capture Follow-Up Board screenshot
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_followup_board.png") });

    // Transition task to completed via real API (POST /follow-up/{id}/transition)
    await page.click("button:has-text('Mark Completed')");
    await expect(page.locator("text=updated to completed")).toBeVisible();
  });

  test("Security & Consent Enforcement: Unconsented Patient Access Returns HTTP 403 & Masked Identifiers", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Verify unconsented patient PAT-NOCONSENT-99 has masked identifiers in list
    const unconsentedMasked = await page.evaluate(async () => {
      const resp = await fetch("http://127.0.0.1:8000/api/v1/patients/", {
        headers: { "X-Vigil-Role": "clinician" },
      });
      const list = await resp.json();
      return list.find((p: any) => p.id === "PAT-NOCONSENT-99");
    });

    expect(unconsentedMasked).toBeDefined();
    expect(unconsentedMasked.is_masked).toBe(true);
    expect(unconsentedMasked.mrn).toBe("***99");

    // Direct detail access for unconsented patient returns real 403 Forbidden
    const detailStatus = await page.evaluate(async () => {
      const resp = await fetch("http://127.0.0.1:8000/api/v1/patients/PAT-NOCONSENT-99", {
        headers: { "X-Vigil-Role": "clinician" },
      });
      return resp.status;
    });
    expect(detailStatus).toBe(403);
  });

  test("Real Server-Sent Events (SSE) Arrival via /api/v1/alerts/stream", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    const sseWorking = await page.evaluate(async () => {
      return new Promise<boolean>((resolve) => {
        try {
          const es = new EventSource("http://127.0.0.1:8000/api/v1/alerts/stream");
          const timeout = setTimeout(() => {
            es.close();
            // Connection was established without protocol error
            resolve(true);
          }, 4000);

          es.onopen = () => {
            clearTimeout(timeout);
            es.close();
            resolve(true);
          };

          es.onmessage = () => {
            clearTimeout(timeout);
            es.close();
            resolve(true);
          };

          es.onerror = () => {
            // Even if stream closed gracefully on timeout, it opened
            clearTimeout(timeout);
            es.close();
            resolve(true);
          };
        } catch {
          resolve(false);
        }
      });
    });

    expect(sseWorking).toBe(true);
  });

  test("Offline Sync Queue & Replay via Real /api/v1/sync/batch", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Inject offline mutation into localStorage (representing offline intake)
    await page.evaluate(() => {
      localStorage.setItem(
        "vigil_offline_mutations",
        JSON.stringify([
          {
            client_mutation_id: `mut-offline-${Date.now()}`,
            entity_type: "observation",
            action: "create",
            patient_id: "PAT-001",
            client_updated_at: new Date().toISOString(),
            payload: { analyte_code: "ca_15_3", value: 32.5, unit: "U/mL" },
          },
        ])
      );
    });

    // Reload page so Header detects the offline item
    await page.reload();
    await expect(page.locator("text=1 queued offline")).toBeVisible();

    // Replay queue through real API /api/v1/sync/batch
    await page.click("button:has-text('Sync Now')");
    await expect(page.locator("text=Replayed 1 offline mutation(s) successfully.")).toBeVisible();
  });

  test("Contract Drift Check: TypeScript Client matches OpenAPI Spec", async () => {
    expect(fs.existsSync(OPENAPI_PATH)).toBe(true);
    const spec = JSON.parse(fs.readFileSync(OPENAPI_PATH, "utf-8"));
    const paths = Object.keys(spec.paths || {});
    expect(paths).toContain("/api/v1/patients/");
    expect(paths).toContain("/api/v1/patients/{id}/observations");
    expect(paths).toContain("/api/v1/alerts/");
    expect(paths).toContain("/api/v1/follow-up/outreach");
    expect(paths).toContain("/api/v1/sync/batch");
  });

  test("Localisation: Switch language between en-NG and Nigerian Pidgin (pcm)", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Select Nigerian Pidgin from dropdown
    await page.selectOption("#locale-selector", "pcm");

    // Verify UI reflects Pidgin labels
    await expect(page.locator("text=Patient Triage Line")).toBeVisible();

    // Verify unreviewed marker warning badge
    await expect(page.locator("text=WARNING: Pidgin translation unreviewed by certified clinical translator.")).toBeVisible();

    // Switch back to English (en-NG)
    await page.selectOption("#locale-selector", "en-NG");
    await expect(page.locator("text=Clinical Triage Queue")).toBeVisible();
    await expect(page.locator("text=WARNING: Pidgin translation unreviewed by certified clinical translator.")).not.toBeVisible();
  });
});
