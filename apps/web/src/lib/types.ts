export interface TargetOrganVector {
  bone: number;
  liver: number;
  lung: number;
  brain: number;
}

export interface Patient {
  id: string;
  age: number;
  created_at: string;
  status: string;
  baseline_profile?: BaselineProfile | null;
  latest_risk?: number | null;
  triage_flag?: boolean;
  latest_justification?: string | null;
}

export interface BaselineProfile {
  id?: string;
  patient_id?: string;
  tumor_stage: number;
  er_status: boolean;
  pr_status: boolean;
  her2_status: boolean;
  has_hypertension: boolean;
  renal_history: boolean;
  target_organ_susceptibility_vector: TargetOrganVector;
}

export interface LabResult {
  id: string;
  patient_id: string;
  date_drawn: string;
  alt_level: number;
  ast_level: number;
  creatinine: number;
  ca_15_3: number;
  wbc_count: number;
}

export interface TrajectoryPoint {
  lab_id: string;
  date_drawn: string;
  alt_level: number;
  ast_level: number;
  creatinine: number;
  ca_15_3: number;
  wbc_count: number;
  calculated_metastasis_risk: number;
  ci_lower?: number;
  ci_upper?: number;
  ca153_velocity_pct?: number;
  alt_velocity_pct?: number;
  triage_flag: boolean;
  justification_text: string;
}

export interface TriageQueueItem {
  patient_id: string;
  age: number;
  status: string;
  tumor_stage?: number | null;
  subtype: string;
  latest_risk: number;
  triage_flag: boolean;
  latest_justification: string;
  target_organ_susceptibility_vector?: TargetOrganVector | null;
  last_lab_date?: string | null;
  total_labs: number;
}

export interface CohortAnalytics {
  total_patients: number;
  scored_patients: number;
  critical_alerts: number;
  watch_cases: number;
  stable_cases: number;
  average_cohort_risk: number;
  organ_tropism_distribution: Record<string, number>;
}

export interface SimulationResult {
  projected_risk: number;
  triage_flag: boolean;
  justification_text: string;
  delta_risk: number;
}
