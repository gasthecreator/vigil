"""
Phase 5: End-to-End Clinical Verification Simulation.
Simulates a real-world patient entering the system:
1. Enrolls patient
2. Submits baseline pathology (triggers Model A XGBoost)
3. Submits 5 sequential longitudinal lab draws (ending in an anomaly cascade)
4. Verifies risk elevates past the 0.75 clinical alert threshold
5. Verifies justification_text cites biomarker velocity and organ concordance
6. Verifies the patient rises to Rank #1 in the prioritized Triage Queue
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/opt/libomp/lib"

from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from sentinel.main import app
from sentinel.database import Base, engine


def run_e2e_simulation():
    print("\n" + "=" * 75)
    print("🚀 EXECUTING PHASE 5: E2E ONCOLOGY SURVEILLANCE SIMULATION")
    print("=" * 75)

    with TestClient(app) as client:
        # Step 1: Enroll Patient
        print("\n[Step 1/5] Enrolling Patient 'Eleanor Vance' (Age: 54, Post-Resection)...")
        p_resp = client.post("/api/v1/patients/", json={"age": 54, "status": "active"})
        assert p_resp.status_code == 201, f"Failed to create patient: {p_resp.text}"
        patient = p_resp.json()
        patient_id = patient["id"]
        print(f"  ✓ Patient enrolled with UUID: {patient_id}")

        # Step 2: Submit Baseline Pathology
        print("\n[Step 2/5] Submitting Baseline Pathology: Stage IIb, ER+, PR-, HER2+...")
        b_resp = client.post(
            f"/api/v1/patients/{patient_id}/baseline",
            json={
                "tumor_stage": 2,
                "er_status": True,
                "pr_status": False,
                "her2_status": True,
                "has_hypertension": False,
                "renal_history": False,
            },
        )
        assert b_resp.status_code == 200, f"Failed baseline: {b_resp.text}"
        baseline = b_resp.json()
        organ_vector = baseline["target_organ_susceptibility_vector"]
        print(f"  ✓ Model A (XGBoost) output organ susceptibility vector:")
        for organ, score in organ_vector.items():
            print(f"    - {organ.capitalize()}: {score * 100:.1f}%")

        # Step 3: Check Initial Triage Position (No labs yet -> risk 0.0)
        triage_init = client.get("/api/v1/patients/triage").json()
        initial_pos = next(i for i, item in enumerate(triage_init) if item["patient_id"] == patient_id)
        print(f"\n  ✓ Initial triage position for new patient: #{initial_pos + 1} (Risk: 0.0%)")

        # Step 4: Submit 5 Longitudinal Labs (3 Normal, 2 Anomalous)
        start_date = datetime.utcnow() - timedelta(days=360)
        lab_protocol = [
            # Visit 1 (Day 0) - Normal baseline
            {
                "date_drawn": (start_date).isoformat(),
                "alt_level": 21.0,
                "ast_level": 19.5,
                "creatinine": 0.82,
                "ca_15_3": 16.2,
                "wbc_count": 6.1,
                "expected_alert": False,
                "label": "Visit 1 (Day 0) - Routine Surveillance Draw",
            },
            # Visit 2 (Day 90) - Normal stable
            {
                "date_drawn": (start_date + timedelta(days=90)).isoformat(),
                "alt_level": 22.5,
                "ast_level": 20.0,
                "creatinine": 0.83,
                "ca_15_3": 17.0,
                "wbc_count": 6.3,
                "expected_alert": False,
                "label": "Visit 2 (Day 90) - Routine Surveillance Draw",
            },
            # Visit 3 (Day 180) - Normal stable
            {
                "date_drawn": (start_date + timedelta(days=180)).isoformat(),
                "alt_level": 24.0,
                "ast_level": 21.0,
                "creatinine": 0.84,
                "ca_15_3": 18.5,
                "wbc_count": 6.4,
                "expected_alert": False,
                "label": "Visit 3 (Day 180) - Routine Surveillance Draw",
            },
            # Visit 4 (Day 270) - Early biological divergence (transaminitis & CA 15-3 velocity)
            {
                "date_drawn": (start_date + timedelta(days=270)).isoformat(),
                "alt_level": 58.0,
                "ast_level": 52.0,
                "creatinine": 0.88,
                "ca_15_3": 38.0,
                "wbc_count": 8.5,
                "expected_alert": False,  # Early warning / watch tier
                "label": "Visit 4 (Day 270) - Sub-clinical Biomarker Acceleration",
            },
            # Visit 5 (Day 360) - Critical recurrence anomaly cascade
            {
                "date_drawn": (start_date + timedelta(days=360)).isoformat(),
                "alt_level": 115.0,
                "ast_level": 94.0,
                "creatinine": 0.91,
                "ca_15_3": 76.5,
                "wbc_count": 11.4,
                "expected_alert": True,   # Critical Alert Threshold >= 0.75
                "label": "Visit 5 (Day 360) - Acute Metastatic Recurrence Cascade",
            },
        ]

        print("\n[Step 3/5] Ingesting 5 Longitudinal Lab Draws into Sentinel Engine...")
        latest_risk = 0.0
        latest_flag = False
        latest_justification = ""

        for idx, lab in enumerate(lab_protocol, start=1):
            res = client.post(
                f"/api/v1/patients/{patient_id}/labs",
                json={
                    "date_drawn": lab["date_drawn"],
                    "alt_level": lab["alt_level"],
                    "ast_level": lab["ast_level"],
                    "creatinine": lab["creatinine"],
                    "ca_15_3": lab["ca_15_3"],
                    "wbc_count": lab["wbc_count"],
                },
            )
            assert res.status_code == 200, f"Lab {idx} failed: {res.text}"
            inference = res.json()
            latest_risk = inference["calculated_metastasis_risk"]
            latest_flag = inference["triage_flag"]
            latest_justification = inference["justification_text"]

            status_symbol = "🚨 ALERT" if latest_flag else "🟢 STABLE"
            print(f"  [{idx}/5] {lab['label']}:")
            print(f"       -> Biomarkers: ALT={lab['alt_level']}, CA 15-3={lab['ca_15_3']}, WBC={lab['wbc_count']}")
            print(f"       -> Model B Risk Score: {latest_risk * 100:.1f}% [{status_symbol}]")

        # Step 4: Verify Final Visit 5 Risk & Alert
        print("\n[Step 4/5] Verifying Alert Threshold & Justification Attributions...")
        assert latest_risk >= 0.75, f"Risk {latest_risk} did not meet clinical alert threshold 0.75!"
        assert latest_flag is True, "Triage flag was not set to True!"
        print(f"  ✓ Model B successfully surpassed alert cutoff: {latest_risk * 100:.1f}% >= 75.0%")
        print(f"  ✓ Triage Flag: {latest_flag}")
        print(f"  ✓ Clinical Justification Synthesized:")
        print(f"     \"{latest_justification}\"")
        assert "ACTIONABLE ALERT" in latest_justification
        assert "CA 15-3" in latest_justification

        # Step 5: Verify Triage Queue Re-Ordering
        print("\n[Step 5/5] Verifying Dynamic Triage Queue Re-Ordering...")
        triage_final = client.get("/api/v1/patients/triage").json()
        assert len(triage_final) > 0

        # Patient should now be at the very top (Rank #1)
        top_patient = triage_final[0]
        print(f"  ✓ Top Roster Patient: {top_patient['patient_id']} (Risk: {top_patient['latest_risk'] * 100:.1f}%)")
        assert top_patient["patient_id"] == patient_id, f"Patient {patient_id} did not rise to Rank #1! Top is {top_patient['patient_id']}"
        assert top_patient["latest_risk"] >= 0.75
        assert top_patient["triage_flag"] is True

        # Verify Trajectory Endpoint Integrity
        traj_resp = client.get(f"/api/v1/patients/{patient_id}/trajectory")
        assert traj_resp.status_code == 200
        traj = traj_resp.json()
        assert len(traj) == 5, f"Expected 5 trajectory points, found {len(traj)}"
        print(f"  ✓ Trajectory endpoint verified with all {len(traj)} chronological visits joined with risks.")

        print("\n" + "=" * 75)
        print("✅ PHASE 5 E2E VERIFICATION COMPLETE: ALL ASSERTIONS PASSED WITH 100% SUCCESS")
        print("=" * 75 + "\n")


if __name__ == "__main__":
    run_e2e_simulation()
