import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import * as path from "path";

const SCREENS_DIR = path.resolve(__dirname, "../../../docs/design/screens");

test.describe("M9 Clinician Workstation E2E Suite", () => {
  test.beforeEach(async ({ page }) => {
    // Mock Core Data Models
    const mockPatients = [
      {
        id: "PAT-001",
        age: 52,
        status: "active",
        mrn: "MRN-UCH-2026-101",
        created_at: "2026-10-01T08:00:00Z",
        synthetic: true,
      },
      {
        id: "PAT-002",
        age: 48,
        status: "active",
        mrn: "MRN-LUTH-2026-202",
        created_at: "2026-10-05T09:30:00Z",
        synthetic: true,
      },
    ];

    const mockAlerts = [
      {
        id: "ALT-PAT-001-01",
        alert_type: "surveillance_anomaly",
        severity: "critical",
        status: "open",
        trigger_reason: "CA 15-3: Significant elevation exceeding RCV",
        created_at: "2026-10-16T14:20:00Z",
      },
    ];

    const mockTasks = [
      {
        task_id: "TSK-001",
        patient_id: "PAT-001",
        task_type: "repeat_specimen",
        status: "pending",
        due_date: "2026-10-18T00:00:00Z",
        escalation_level: 2,
        notes: "Surveillance guardian alert: repeat confirmation draw required",
        synthetic: true,
      },
      {
        task_id: "TSK-002",
        patient_id: "PAT-002",
        task_type: "clinical_review",
        status: "in_progress",
        due_date: "2026-10-25T00:00:00Z",
        escalation_level: 0,
        notes: "Routine quarterly follow-up",
        synthetic: true,
      },
    ];

    const mockObservations: Record<string, any[]> = {
      "PAT-001": [
        {
          id: "OBS-001",
          analyte_code: "ca_15_3",
          value: 245.0,
          unit: "U/mL",
          specimen_collected_at: "2026-10-16T12:00:00Z",
          quality_flags: {
            action: "needs_repeat",
            p_real: 0.18,
            p_error: 0.74,
            p_stable: 0.08,
            alert_id: "ALT-PAT-001-01",
            task_id: "TSK-001",
            narrative: "Surprising CA 15-3 level 245.0 U/mL is 10.4x above personal baseline (23.5 U/mL). Reference Change Value (RCV 28.5%) exceeded. Plausibility model assigns 74% probability to pre-analytical or analytical anomaly. Zero-dismissal invariant enforced: Confirmation draw recommended within 7–14 days before imaging escalation.",
          },
        },
        {
          id: "OBS-000",
          analyte_code: "ca_15_3",
          value: 23.5,
          unit: "U/mL",
          specimen_collected_at: "2026-07-15T10:00:00Z",
          quality_flags: {
            action: "explained",
            p_real: 0.02,
            p_error: 0.01,
            p_stable: 0.97,
            narrative: "Biomarker stable within expected biological variation.",
          },
        },
      ],
      "PAT-002": [
        {
          id: "OBS-002",
          analyte_code: "ca_15_3",
          value: 18.2,
          unit: "U/mL",
          specimen_collected_at: "2026-09-10T11:00:00Z",
          quality_flags: {
            action: "explained",
            p_real: 0.01,
            p_error: 0.01,
            p_stable: 0.98,
            narrative: "Baseline within normal reference limits.",
          },
        },
      ],
    };

    const mockRiskHistory: Record<string, any[]> = {
      "PAT-001": [
        {
          id: "RSK-001",
          score: 0.68,
          risk_tier: "elevated",
          adjudicated_action: "needs_repeat",
          assessment_date: "2026-10-16T12:05:00Z",
          uncertainty: { lower: 0.59, upper: 0.77 },
          input_hash: "sha256:7b91d...",
          model_versions: { k8_conformal: "v1.2", m3_adjudicator: "v2.0" },
        },
      ],
      "PAT-002": [
        {
          id: "RSK-002",
          score: 0.12,
          risk_tier: "low",
          adjudicated_action: "explained",
          assessment_date: "2026-09-10T11:05:00Z",
          uncertainty: { lower: 0.08, upper: 0.17 },
          input_hash: "sha256:4a12e...",
          model_versions: { k8_conformal: "v1.2", m3_adjudicator: "v2.0" },
        },
      ],
    };

    // Route Interception Dispatcher
    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const p = url.pathname;
      const method = req.method();

      if (p === "/api/v1/patients" || p === "/api/v1/patients/") {
        if (method === "POST") {
          const body = JSON.parse(req.postData() || "{}");
          const newPt = {
            id: `PAT-00${mockPatients.length + 1}`,
            age: body.age || 54,
            status: body.status || "active",
            mrn: body.mrn || "MRN-ENCRYPTED",
            created_at: new Date().toISOString(),
            synthetic: true,
          };
          mockPatients.push(newPt);
          await route.fulfill({ status: 201, json: newPt });
        } else {
          await route.fulfill({ json: mockPatients });
        }
        return;
      }

      if (p.includes("/consent")) {
        await route.fulfill({ json: { status: "granted" } });
        return;
      }

      if (p.includes("/observations")) {
        const pId = p.split("/")[4];
        if (method === "POST") {
          const body = JSON.parse(req.postData() || "{}");
          const newObs = {
            id: `OBS-${Date.now()}`,
            analyte_code: body.analyte_code,
            value: body.value,
            unit: body.unit,
            specimen_collected_at: body.specimen_date || new Date().toISOString(),
            quality_flags: {
              action: body.value > 100 ? "needs_repeat" : "explained",
              p_real: body.value > 100 ? 0.15 : 0.05,
              p_error: body.value > 100 ? 0.80 : 0.02,
              p_stable: body.value > 100 ? 0.05 : 0.93,
              alert_id: "ALT-PAT-001-01",
              task_id: "TSK-001",
              narrative: body.value > 100
                ? "Surprising CA 15-3 level 245.0 U/mL is 10.4x above personal baseline (23.5 U/mL). Reference Change Value (RCV 28.5%) exceeded. Plausibility model assigns 74% probability to pre-analytical or analytical anomaly. Zero-dismissal invariant enforced: Confirmation draw recommended within 7–14 days before imaging escalation."
                : "Biomarker stable within expected biological variation.",
            },
          };
          if (!mockObservations[pId]) mockObservations[pId] = [];
          mockObservations[pId].unshift(newObs);
          await route.fulfill({
            status: 201,
            json: {
              observation_id: newObs.id,
              patient_id: pId,
              risk_assessment_id: "RSK-NEW-01",
              action: newObs.quality_flags.action,
            },
          });
        } else {
          await route.fulfill({ json: mockObservations[pId] || [] });
        }
        return;
      }

      if (p.includes("/risk-history")) {
        const pId = p.split("/")[4];
        await route.fulfill({ json: mockRiskHistory[pId] || [] });
        return;
      }

      if (p.startsWith("/api/v1/patients/")) {
        const pId = p.split("/")[4];
        const pt = mockPatients.find((ptObj) => ptObj.id === pId) || mockPatients[0];
        await route.fulfill({ json: pt });
        return;
      }

      if (p.startsWith("/api/v1/alerts")) {
        if (p.includes("/acknowledge")) {
          const body = JSON.parse(req.postData() || "{}");
          await route.fulfill({
            json: {
              alert_id: "ALT-ACK-01",
              status: "acknowledged",
              disposition: body.disposition,
              rationale_text: body.rationale_text,
              acknowledged_by: "USR-CLINICIAN-01",
              acknowledged_at: new Date().toISOString(),
            },
          });
          return;
        }
        await route.fulfill({ json: mockAlerts });
        return;
      }

      if (p.startsWith("/api/v1/follow-up")) {
        if (p.includes("/transition")) {
          const body = JSON.parse(req.postData() || "{}");
          const taskId = p.split("/")[4];
          const task = mockTasks.find((t) => t.task_id === taskId);
          if (task) task.status = body.target_status;
          await route.fulfill({
            json: {
              task_id: taskId,
              patient_id: "PAT-001",
              status: body.target_status,
              task_type: "repeat_specimen",
              due_date: new Date().toISOString(),
              escalation_level: 0,
            },
          });
          return;
        }
        await route.fulfill({ json: mockTasks });
        return;
      }

      if (p.includes("/sync/batch")) {
        const body = JSON.parse(req.postData() || "{}");
        const count = body.mutations?.length || 0;
        await route.fulfill({
          json: {
            sync_id: body.sync_id || "sync-01",
            total_mutations: count,
            applied_count: count,
            already_applied_count: 0,
            conflict_count: 0,
            rejected_count: 0,
            processed_at: new Date().toISOString(),
            results: body.mutations?.map((m: any) => ({
              client_mutation_id: m.client_mutation_id,
              status: "applied",
              entity_id: "ENT-SYNC-01",
            })) || [],
          },
        });
        return;
      }

      await route.fulfill({ json: {} });
    });
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
    await page.fill("input[placeholder='e.g. MRN-UCH-2026-981']", "MRN-UCH-2026-981");
    await page.fill("input[type='number']", "54");
    await page.selectOption("#stage-select", "Stage II");
    await page.selectOption("#subtype-select", "HR+HER2-");

    // Submit Enrolment & Consent
    await page.click("button:has-text('Enrol & Grant Consent')");

    // Verify confirmation and modal dismissal
    await expect(page.locator("text=successfully enrolled with clinical care consent")).toBeVisible();
    await page.waitForTimeout(800);

    // Capture visual snapshot of triage queue
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_triage.png"), fullPage: true });

    // Verify synthetic watermark banner is prominently displayed
    await expect(page.locator("header").getByText("RESEARCH PROTOTYPE")).toBeVisible();
    await expect(page.locator("header").getByText("SYNTHETIC DATASET")).toBeVisible();
  });

  test("Journey J2: Ingest Surprising CA 15-3 Spike → M3 Plausibility Adjudication → Zero-Dismissal Invariant", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Open Intake Drawer via Add Observation button
    await page.click("button:has-text('Add Observation (Intake)')");
    await expect(page.locator("h2:has-text('Fast Observation Intake')")).toBeVisible();

    // Take screenshot of intake modal
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_intake_modal.png") });

    // Enter surprising value (240 U/mL)
    await page.fill("input[placeholder='e.g. 24.5']", "240.0");
    await page.click("button:has-text('Submit to Surveillance Pipeline')");

    await expect(page.locator("text=Observation recorded successfully")).toBeVisible();
    await page.waitForTimeout(1100);

    // Verify Zero-Dismissal Invariant: classified as needs_repeat, NOT dismissed
    await expect(page.locator("text=NEEDS CONFIRMATION (needs_repeat)")).toBeVisible();
    await expect(page.getByText("DISMISSED", { exact: true })).not.toBeVisible();

    // Verify 3-way Bayesian mixture probabilities are rendered
    await expect(page.locator("text=Analytical/Pre-Analytical Error")).toBeVisible();
    await expect(page.locator("text=Real Disease Progression")).toBeVisible();

    // Verify M5 Narrative explains RCV exceeding personal baseline
    await expect(page.locator("text=Surprising CA 15-3 level 245.0 U/mL")).toBeVisible();

    // Capture M3 Adjudication Panel screenshot
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_m3_adjudication.png") });

    // Action: Order Repeat Specimen (7d)
    await page.click("button:has-text('Order Repeat Specimen (7d)')");
    await expect(page.locator("text=protocol initiated")).toBeVisible();
  });

  test("Journey J3: Follow-Up Guardian → Reminder Cascade Escalation → Mark Completed", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Switch to Follow-Up Tasks tab
    await page.click("button:has-text('Follow-Up Guardian (M6)')");

    // Verify urgent escalation level badge
    await expect(page.locator("text=URGENT (ESC L2+)")).toBeVisible();

    // Capture Follow-Up Board screenshot
    await page.screenshot({ path: path.join(SCREENS_DIR, "m9_workstation_followup_board.png") });

    // Transition task to completed
    await page.click("button:has-text('Mark Completed')");
    await expect(page.locator("text=updated to completed")).toBeVisible();
  });

  test("Offline Sync Queue & Replay via /sync/batch", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("header");

    // Inject offline mutation into localStorage
    await page.evaluate(() => {
      localStorage.setItem(
        "vigil_offline_mutations",
        JSON.stringify([
          {
            client_mutation_id: "mut-offline-e2e-01",
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

    // Replay queue
    await page.click("button:has-text('Sync Now')");
    await expect(page.locator("text=Replayed 1 offline mutation(s) successfully.")).toBeVisible();
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
