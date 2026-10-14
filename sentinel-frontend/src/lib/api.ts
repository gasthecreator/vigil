import {
  Patient,
  BaselineProfile,
  TrajectoryPoint,
  TriageQueueItem,
  CohortAnalytics,
  SimulationResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchTriageQueue(): Promise<TriageQueueItem[]> {
  const res = await fetch(`${API_BASE}/patients/triage`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch triage queue");
  return res.json();
}

export async function fetchPatientDetail(id: string): Promise<Patient> {
  const res = await fetch(`${API_BASE}/patients/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch patient details");
  return res.json();
}

export async function fetchPatientTrajectory(id: string): Promise<TrajectoryPoint[]> {
  const res = await fetch(`${API_BASE}/patients/${id}/trajectory`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch patient trajectory");
  return res.json();
}

export async function fetchCohortAnalytics(): Promise<CohortAnalytics> {
  const res = await fetch(`${API_BASE}/analytics/cohort`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch cohort analytics");
  return res.json();
}

export async function createPatient(data: { age: number; status?: string }): Promise<Patient> {
  const res = await fetch(`${API_BASE}/patients/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to enroll patient");
  return res.json();
}

export async function submitBaseline(
  patientId: string,
  data: {
    tumor_stage: number;
    er_status: boolean;
    pr_status: boolean;
    her2_status: boolean;
    has_hypertension: boolean;
    renal_history: boolean;
  }
): Promise<BaselineProfile> {
  const res = await fetch(`${API_BASE}/patients/${patientId}/baseline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit baseline pathology");
  return res.json();
}

export async function submitLabResult(
  patientId: string,
  data: {
    date_drawn?: string;
    alt_level: number;
    ast_level: number;
    creatinine: number;
    ca_15_3: number;
    wbc_count: number;
  }
): Promise<any> {
  const res = await fetch(`${API_BASE}/patients/${patientId}/labs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit lab result");
  return res.json();
}

export async function simulateFutureLab(
  patientId: string,
  hypotheticalLab: {
    alt_level: number;
    ast_level: number;
    creatinine: number;
    ca_15_3: number;
    wbc_count: number;
  }
): Promise<SimulationResult> {
  const res = await fetch(`${API_BASE}/patients/${patientId}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hypothetical_lab: hypotheticalLab }),
  });
  if (!res.ok) throw new Error("Simulation failed");
  return res.json();
}
