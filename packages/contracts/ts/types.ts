/**
 * Auto-generated TypeScript types for Vigil Precision Oncology Platform API.
 * Generated from docs/api/openapi.json. DO NOT EDIT DIRECTLY.
 */

export interface AlertAcknowledgeRequest {
  /** Disposition code from AlertDisposition */
  disposition: string;
  /** Clinician note or justification */
  note?: string | null;
  /** Clinician justification for alert disposition */
  rationale_text?: string | null;
}

export interface AlertAcknowledgeResponse {
  acknowledged_at: string /* ISO 8601 */;
  acknowledged_by: string;
  alert_id: string;
  disposition: string;
  rationale_text: string;
  status: string;
  synthetic?: boolean;
}

export interface AlertSummary {
  alert_type: string;
  created_at: string /* ISO 8601 */;
  id: string;
  severity: string;
  status: string;
  trigger_reason: string;
}

export interface AuditVerifyResponse {
  error?: string | null;
  head_hash?: string | null;
  tampered_event_id?: string | null;
  total_events: number;
  valid: boolean;
  verified_events: number;
}

export interface BaselineCreate {
  /** Estrogen Receptor status (ER+/-) */
  er_status: boolean;
  /** Hypertension comorbidity */
  has_hypertension?: boolean;
  /** HER2 receptor amplification status (HER2+/-) */
  her2_status: boolean;
  /** Progesterone Receptor status (PR+/-) */
  pr_status: boolean;
  /** Chronic renal disease history */
  renal_history?: boolean;
  /** Primary tumor stage (1-4) */
  tumor_stage: number;
}

export interface BaselineResponse {
  er_status: boolean;
  has_hypertension: boolean;
  her2_status: boolean;
  id: string;
  patient_id: string;
  pr_status: boolean;
  renal_history: boolean;
  target_organ_susceptibility_vector: TargetOrganVector;
  tumor_stage: number;
}

export interface BatchImportResponse {
  duplicate_count: number;
  imported_count: number;
  rejected_count: number;
  row_reports: RowReport[];
  total_rows: number;
}

export interface ConsentCreateRequest {
  /** Type of clinical consent */
  consent_type?: string;
  /** Expiration date */
  expires_at?: string /* ISO 8601 */ | null;
  /** Whether consent is granted */
  granted?: boolean;
  /** Consent scope e.g. clinical_care, full */
  scope?: string;
  /** Withdrawal date */
  withdrawn_at?: string /* ISO 8601 */ | null;
}

export interface FollowUpTaskResponse {
  due_date: string /* ISO 8601 */;
  escalation_level: number;
  notes?: string | null;
  patient_id: string;
  status: string;
  synthetic?: boolean;
  task_id: string;
  task_type: string;
}

export interface FollowUpTaskSummary {
  due_date: string /* ISO 8601 */;
  escalation_level: number;
  id: string;
  notes?: string | null;
  status: string;
  task_type: string;
}

export interface FollowUpTransitionRequest {
  /** Optional clinical note explaining state transition */
  reason?: string | null;
  /** Target status from FollowUpTaskStatus */
  target_status: string;
}

export interface HL7ORUImportResponse {
  imported_count: number;
  message_control_id: string;
  observation_reports: HL7ObservationImportReport[];
  patient_id: string;
  rejected_count: number;
  total_observations: number;
}

export interface HL7ObservationImportReport {
  adjudicated_action?: string | null;
  alert_created?: boolean;
  analyte_code: string;
  errors?: string[];
  loinc_code?: string | null;
  observation_id?: string | null;
  set_id: number;
  status: string;
  task_created?: boolean;
  unit: string;
  value: number;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface LabResultCreate {
  /** Alanine Transaminase (U/L) */
  alt_level: number;
  /** Aspartate Transaminase (U/L) */
  ast_level: number;
  /** Cancer Antigen 15-3 (U/mL) */
  ca_15_3: number;
  /** Serum Creatinine (mg/dL) */
  creatinine: number;
  /** Date and time blood specimen was drawn */
  date_drawn?: string /* ISO 8601 */ | null;
  /** White Blood Cell count (x10^9/L) */
  wbc_count: number;
}

export interface ObservationCreateRequest {
  /** Analyte code from vigil_core.analytes (e.g. 'ca_15_3', 'cea') */
  analyte_code: string;
  /** Flag indicating if analyzer/lab changed from previous draw */
  lab_changed?: boolean;
  /** Identifier of executing laboratory */
  laboratory_id?: string | null;
  /** Timestamp when specimen was drawn */
  specimen_collected_at?: string /* ISO 8601 */ | null;
  /** Input unit string (e.g. 'U/mL', 'kU/L', '[iU]/mL') */
  unit: string;
  /** Observed raw numeric value */
  value: number;
}

export interface ObservationCreateResponse {
  adjudicated_action: string;
  alert?: AlertSummary | null;
  analyte_code: string;
  canonical_unit: string;
  canonical_value: number;
  follow_up_task?: FollowUpTaskSummary | null;
  observation_id: string;
  patient_id: string;
  plausibility_status: string;
  raw_unit: string;
  raw_value: number;
  risk_assessment: RiskAssessmentSummary;
  specimen_collected_at: string /* ISO 8601 */;
  synthetic?: boolean;
}

export interface PatientCreate {
  /** Patient age in years */
  age: number;
  /** Clinical surveillance status */
  status?: string;
}

export interface PatientResponse {
  age: number;
  created_at: string /* ISO 8601 */;
  id: string;
  status: string;
}

export interface RiskAssessmentSummary {
  abstention?: boolean;
  adjudicated_action: string;
  assessment_date: string /* ISO 8601 */;
  clinical_note?: string | null;
  id: string;
  input_hash: string;
  model_versions: Record<string, string>;
  risk_tier: string;
  score: number;
  uncertainty?: Record<string, unknown> | null;
}

export interface RiskInferenceResponse {
  calculated_metastasis_risk: number;
  created_at: string /* ISO 8601 */;
  id: string;
  justification_text: string;
  lab_result_id: string;
  patient_id: string;
  triage_flag: boolean;
}

export interface RowReport {
  adjudicated_action?: string | null;
  alert_created?: boolean;
  analyte_code: string;
  errors?: string[];
  observation_id?: string | null;
  patient_id: string;
  row_index: number;
  status: string;
  task_created?: boolean;
  unit?: string | null;
  value?: number | null;
}

export interface SimulationRequest {
  hypothetical_lab: Record<string, number>;
}

export interface SimulationResponse {
  delta_risk: number;
  justification_text: string;
  projected_risk: number;
  triage_flag: boolean;
}

export interface SyncBatchRequest {
  /** Originating device or workstation ID */
  client_device_id?: string | null;
  /** Timestamp when batch was dispatched */
  client_timestamp: string /* ISO 8601 */;
  /** Array of queued mutations */
  mutations: SyncMutationItem[];
  /** Unique client batch transaction identifier */
  sync_id: string;
}

export interface SyncBatchResponse {
  already_applied_count: number;
  applied_count: number;
  conflict_count: number;
  processed_at: string;
  rejected_count: number;
  results: SyncMutationResult[];
  sync_id: string;
  total_mutations: number;
}

export interface SyncMutationItem {
  /** 'create' or 'update' */
  action?: string;
  /** Unique client-generated idempotency key */
  client_mutation_id: string;
  /** Client timestamp when mutation occurred */
  client_updated_at: string /* ISO 8601 */;
  /** Target entity ID if updating */
  entity_id?: string | null;
  /** 'observation', 'follow_up_task', or 'alert_acknowledgement' */
  entity_type: string;
  /** Target patient UUID */
  patient_id: string;
  /** Mutation payload */
  payload: Record<string, unknown>;
}

export interface SyncMutationResult {
  client_mutation_id: string;
  details?: Record<string, unknown> | null;
  entity_id?: string | null;
  error?: string | null;
  server_updated_at?: string | null;
  status: string;
}

export interface TargetOrganVector {
  bone: number;
  brain: number;
  liver: number;
  lung: number;
}

export interface TrajectoryPoint {
  alt_level: number;
  alt_velocity_pct?: number | null;
  ast_level: number;
  ca153_velocity_pct?: number | null;
  ca_15_3: number;
  calculated_metastasis_risk: number;
  ci_lower?: number | null;
  ci_upper?: number | null;
  creatinine: number;
  date_drawn: string /* ISO 8601 */;
  justification_text: string;
  lab_id: string;
  triage_flag: boolean;
  wbc_count: number;
}

export interface TriageQueueItem {
  action_urgency?: number;
  age: number;
  last_lab_date?: string /* ISO 8601 */ | null;
  latest_justification: string;
  latest_risk: number;
  patient_id: string;
  status: string;
  subtype?: string;
  target_organ_susceptibility_vector?: Record<string, number> | null;
  total_labs?: number;
  triage_flag: boolean;
  tumor_stage?: number | null;
  urgency_breakdown?: Record<string, number> | null;
}

export interface ValidationError {
  ctx?: Record<string, unknown>;
  input?: unknown;
  loc: string | number[];
  msg: string;
  type: string;
}
