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
  target_organ_susceptibility_vector: TargetOrganVector | null;
  tumor_stage: number;
}

export interface BatchImportResponse {
  duplicate_count: number;
  imported_count: number;
  rejected_count: number;
  row_reports: RowReport[];
  total_rows: number;
}

export interface CaregiverShareCreateRequest {
  /** Name of the family caregiver */
  caregiver_name: string;
  /** Validity period in days */
  expires_in_days?: number;
  /** Relationship (e.g. daughter, spouse, sibling) */
  relationship_type?: string;
  /** Access scope: view_summary or full_history */
  scope?: string;
}

export interface CaregiverShareResponse {
  caregiver_name: string;
  created_at: string /* ISO 8601 */;
  expires_at: string /* ISO 8601 */;
  id: string;
  patient_id: string;
  relationship_type: string;
  revoked_at?: string /* ISO 8601 */ | null;
  scope: string;
  share_token?: string | null;
  status: string;
  synthetic?: boolean;
  token_preview: string;
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

export interface DelayLedgerEntryResponse {
  clinician_overridden?: boolean;
  course_id: string;
  created_at: string /* ISO 8601 */;
  delay_days: number;
  id: string;
  marginal_harm?: number | null;
  moved_from_date?: string /* ISO 8601 */ | null;
  moved_to_date: string /* ISO 8601 */;
  patient_id: string;
  reason: string;
  recorded_by?: string;
  synthetic?: boolean;
}

export interface DisclosureLockRequest {
  /** Reason for re-locking disclosure */
  reason?: string | null;
}

export interface DisclosureLockResponse {
  locked?: boolean;
  locked_at: string /* ISO 8601 */;
  message: string;
  synthetic?: boolean;
}

export interface DisclosureReleaseRequest {
  /** Reason or patient note for requesting clinician release */
  reason?: string | null;
}

export interface DisclosureReleaseRequestResponse {
  message: string;
  requested?: boolean;
  synthetic?: boolean;
  task_id: string;
}

export interface DisclosureUnlockRequest {
  /** Reason for unlocking bad news / sensitive result */
  reason?: string | null;
}

export interface DisclosureUnlockResponse {
  message: string;
  synthetic?: boolean;
  unlocked: boolean;
  unlocked_at: string /* ISO 8601 */;
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

export interface GovernanceApprovalRequest {
  evaluation_id: string;
}

export interface GovernanceRollbackRequest {
  reason: string;
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

export interface LabSubmissionResponse {
  calculated_metastasis_risk: null;
  lab_result_id: string;
  message: string;
  outputs_withheld: boolean;
  patient_id: string;
  status: "recorded" | "unavailable";
  triage_flag: null;
}

export interface LinacMachineResponse {
  created_at: string /* ISO 8601 */;
  daily_slot_capacity: number;
  downtime_started_at?: string /* ISO 8601 */ | null;
  expected_return_at?: string /* ISO 8601 */ | null;
  facility_id?: string | null;
  id: string;
  machine_name: string;
  status: string;
  synthetic?: boolean;
  updated_at: string /* ISO 8601 */;
}

export interface LinacMachineStatusUpdate {
  /** Expected time machine will return to operational status */
  expected_return_at?: string /* ISO 8601 */ | null;
  /** Reason for downtime or maintenance */
  reason?: string | null;
  /** Machine status: operational, down, maintenance */
  status: string;
}

export interface ModelGovernanceObservation {
  day: number;
  value?: number | null;
}

export interface ModelGovernanceSeries {
  observations: ModelGovernanceObservation[];
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
  outputs_withheld?: boolean;
  patient_id: string;
  plausibility_status: string;
  raw_unit: string;
  raw_value: number;
  risk_assessment?: RiskAssessmentSummary | null;
  specimen_collected_at: string /* ISO 8601 */;
  synthetic?: boolean;
}

export interface OcrConfusionFlag {
  field: string;
  reason: string;
}

export interface OcrDraftConfirmRequest {
  analyte_code: string;
  /** Must be true. The server never copies OCR suggestions into an observation. */
  confirmed: true;
  lab_changed?: boolean;
  laboratory_id?: string | null;
  specimen_collected_at: string /* ISO 8601 */;
  unit: string;
  value: number;
}

export interface OcrDraftConfirmResponse {
  adjudicated_action: string;
  alert?: AlertSummary | null;
  analyte_code: string;
  canonical_unit: string;
  canonical_value: number;
  draft_id: string;
  draft_status?: string;
  follow_up_task?: FollowUpTaskSummary | null;
  observation_id: string;
  outputs_withheld?: boolean;
  patient_id: string;
  plausibility_status: string;
  raw_unit: string;
  raw_value: number;
  risk_assessment?: RiskAssessmentSummary | null;
  specimen_collected_at: string /* ISO 8601 */;
  synthetic?: boolean;
}

export interface OcrDraftResponse {
  confusion_flags: OcrConfusionFlag[];
  content_type: string;
  created_at: string /* ISO 8601 */;
  created_by: string;
  engine: string;
  extracted_text: string;
  filename: string;
  id: string;
  notice?: string;
  observation_id?: string | null;
  patient_id: string;
  resolved_at?: string /* ISO 8601 */ | null;
  resolved_by?: string | null;
  source_sha256: string;
  status: string;
  suggestion: OcrSuggestion;
  synthetic?: boolean;
}

export interface OcrDraftUploadRequest {
  /** Base64 of the PNG, JPEG or PDF bytes */
  content_base64: string;
  content_type: string;
  filename: string;
}

export interface OcrSuggestion {
  analyte_code?: string | null;
  analyte_name?: string | null;
  flags?: OcrConfusionFlag[];
  specimen_collected_at?: string | null;
  unit?: string | null;
  value?: number | null;
}

export interface PatientCreate {
  /** Patient age in years */
  age: number;
  /** External hospital system identifier (encrypted at rest) */
  external_id?: string | null;
  /** Medical Record Number (encrypted at rest) */
  mrn?: string | null;
  /** Clinical surveillance status */
  status?: string;
}

export interface PatientDelayNoticeResponse {
  clinical_context?: string | null;
  course_id?: string | null;
  delay_history?: DelayLedgerEntryResponse[];
  expected_start_date?: string /* ISO 8601 */ | null;
  has_active_treatment: boolean;
  machine_name?: string | null;
  machine_status?: string | null;
  patient_id: string;
  plain_language_notice: string;
  synthetic?: boolean;
  total_delay_days?: number;
}

export interface PatientResponse {
  age?: number | null;
  created_at: string /* ISO 8601 */;
  external_id?: string | null;
  id: string;
  /** True if medical identifiers are redacted due to absence of active consent */
  is_masked?: boolean;
  mrn?: string | null;
  status: string;
}

export interface PatientUpdate {
  /** Patient age in years */
  age?: number | null;
  /** External hospital system identifier (encrypted at rest) */
  external_id?: string | null;
  /** Medical Record Number (encrypted at rest) */
  mrn?: string | null;
  /** Clinical surveillance status */
  status?: string | null;
}

export interface PlainLanguageExplainerResponse {
  analyte_code: string;
  flesch_kincaid_grade_level: number;
  headline: string;
  observation_id: string;
  patient_id: string;
  questions_to_ask_your_doctor: string[];
  recommended_action: string;
  synthetic?: boolean;
  verbal_band: string;
  verdict: string;
  verified?: boolean;
  what_this_means: string;
  word_count: number;
}

export interface QualityAuditRequest {
  /** Optional facility identifier to filter trajectories */
  facility_id?: string | null;
  /** Run the audit on the built-in SYNTHETIC benchmark cohort only (never mixed with facility data) */
  include_synthetic_benchmark?: boolean;
  /** Lookback window in days for surveillance audit */
  lookback_days?: number;
  /** Bootstrap iterations for confidence intervals */
  n_bootstrap?: number;
}

export interface QualityAuditResponse {
  audit_id: string;
  facility_id?: string | null;
  narrative_summary: string;
  overall_action_not_recorded_rate: number;
  overall_bootstrap_ci_95: number[];
  register_audit_verified?: boolean;
  stage_breakdown: Record<string, StratumAuditMetricResponse>;
  subgroup_breakdown: Record<string, StratumAuditMetricResponse>;
  subtype_breakdown: Record<string, StratumAuditMetricResponse>;
  suppressed_strata_count: number;
  /** True only when this response was computed from the built-in synthetic benchmark cohort. */
  synthetic: boolean;
  total_action_not_recorded: number;
  total_action_recorded: number;
  total_patients_audited: number;
  total_signals_detected: number;
}

export interface RadiotherapyCourseCreate {
  assigned_machine_id?: string | null;
  baseline_subgroup?: string | null;
  /** Clinical context: adjuvant_post_lumpectomy, adjuvant_post_mastectomy, curative_tnbc, palliative_bone_brain */
  clinical_context?: string;
  patient_id: string;
  prescribed_start_date: string /* ISO 8601 */;
  total_fractions?: number;
  /** Urgency tier: emergency, urgent, routine */
  urgency_tier?: string;
}

export interface RadiotherapyCourseResponse {
  actual_start_date?: string /* ISO 8601 */ | null;
  assigned_machine_id?: string | null;
  baseline_subgroup?: string | null;
  clinical_context: string;
  created_at: string /* ISO 8601 */;
  current_delay_days?: number;
  expected_excess_harm?: number;
  fractions_delivered: number;
  id: string;
  patient_id: string;
  prescribed_start_date: string /* ISO 8601 */;
  scheduled_start_date?: string /* ISO 8601 */ | null;
  status: string;
  synthetic?: boolean;
  total_fractions: number;
  updated_at: string /* ISO 8601 */;
  urgency_tier: string;
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

export interface ScheduleAssignment {
  context: string;
  course_id: string;
  delay_days: number;
  explanation: string;
  fractions: number;
  is_moved?: boolean;
  machine_id: string;
  marginal_harm: number;
  patient_id: string;
  priority_rank?: number | null;
  scheduled_date: string /* ISO 8601 */;
  start_day: number;
}

export interface ScheduleConfirmRequest {
  assignments: ScheduleAssignment[];
  /** Clinical rationale for confirming the schedule reallocation */
  reason?: string | null;
}

export interface ScheduleConfirmResponse {
  audit_event_id: string;
  confirmed?: boolean;
  ledger_entries_created: number;
  message: string;
  synthetic?: boolean;
}

/** Request a schedule proposal.

``method`` defaults to the explainable urgency ranking (ADR-0019). The CP-SAT
optimiser is a research module: it is only available to
administrators (or when the deployment sets ``VIGIL_ENABLE_RESEARCH_SCHEDULER=1``)
and is always labelled ``unvalidated in simulation``. ``fairness_disparity_bound``,
``max_wait_days`` and ``stability_penalty`` apply to the CP-SAT method only. */
export interface ScheduleSolveRequest {
  fairness_disparity_bound?: number;
  horizon_days?: number;
  max_wait_days?: number;
  method?: "urgency_ranking" | "cpsat_research";
  stability_penalty?: number;
}

export interface ScheduleSolveResponse {
  assignments: ScheduleAssignment[];
  fairness_bound_enforced?: boolean;
  fairness_disparity: number;
  max_delay_days: number;
  mean_delay_days: number;
  method?: string;
  method_label?: string;
  patients_included?: number;
  patients_unconsented_included?: number;
  solver_time_seconds: number;
  status: string;
  synthetic?: boolean;
  total_excess_harm: number;
  unassigned_patient_ids: string[];
  validation_status?: string;
  warnings?: string[];
}

export interface SecondLookCreateRequest {
  /** ID of observation to be re-evaluated */
  observation_id: string;
  /** Questions or context from patient/caregiver */
  patient_notes?: string | null;
  /** Requested clinical review action */
  requested_action?: string | null;
}

export interface SecondLookResponse {
  analyte_code: string;
  created_at: string /* ISO 8601 */;
  notes?: string | null;
  observation_id: string;
  patient_id: string;
  plausibility_status: string;
  status: string;
  synthetic?: boolean;
  task_id: string;
  unit: string;
  value: number;
}

export interface ShadowEvaluationRequest {
  candidate_id: string;
  /** Pre-declared criterion; absolute series rate increase */
  max_alert_rate_increase: number;
  monitor_report: Record<string, unknown>;
  series: ModelGovernanceSeries[];
}

export interface SimulationRequest {
  hypothetical_lab: Record<string, number>;
}

export interface SimulationResponse {
  delta_risk: number | null;
  justification_text: string;
  message: string;
  projected_risk: number | null;
  status: "abstained";
  triage_flag: boolean | null;
}

export interface StratumAuditMetricResponse {
  action_not_recorded_count: number | string;
  action_not_recorded_rate?: number | null;
  is_suppressed?: boolean;
  stratum_name: string;
  total_signals: number | string;
}

export interface SymptomCreateRequest {
  /** Input modality e.g. text or voice */
  input_modality?: string;
  /** Patient/caregiver description or notes */
  notes?: string | null;
  /** Timestamp of symptom experience */
  recorded_at?: string /* ISO 8601 */ | null;
  /** Severity grade (1=Mild, 2=Moderate, 3=Severe, 4=Very Severe) */
  severity?: number;
  /** Name/category of symptom (e.g. bone_pain, fatigue) */
  symptom_name: string;
}

export interface SymptomResponse {
  created_at: string /* ISO 8601 */;
  id: string;
  input_modality?: string;
  notes?: string | null;
  patient_id: string;
  recorded_at: string /* ISO 8601 */;
  severity: number;
  symptom_name: string;
  synthetic?: boolean;
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

export interface TestLadderAvailabilityFeedback {
  available: boolean;
  facility_id: string;
  modality: string;
  price_band: number;
  source: string;
  turnaround_days?: number | null;
  verified_on: string;
}

export interface TestLadderFacility {
  facility_id: string;
  modalities: TestLadderModalityRow[];
  name: string;
  tier: string;
}

export interface TestLadderModalityRow {
  available: boolean;
  /** 1 nearest to 4 farthest */
  distance_band: number;
  modality: string;
  /** 1 lowest to 4 highest */
  price_band: number;
  /** Who reported this row */
  source: string;
  turnaround_days?: number | null;
  /** Date the row was last confirmed */
  verified_on?: string | null;
}

/** Probability that the organ is involved, as an interval with a stated provenance. */
export interface TestLadderPrior {
  /** Defaults to value */
  hi?: number | null;
  /** Defaults to value */
  lo?: number | null;
  /** Where the prior came from */
  provenance: string;
  value: number;
}

/** Stateless request. Exactly one of ``facility_id`` (registry template) or ``facility`` (inline rows). */
export interface TestLadderRequest {
  /** Date for staleness; defaults to the server date, never later */
  as_of?: string | null;
  facility?: TestLadderFacility | null;
  /** A registry facility id (illustrative templates ship) */
  facility_id?: string | null;
  /** Highest price band the patient has agreed to; tests above it are skipped */
  max_price_band?: number | null;
  organ: "bone" | "liver" | "lung" | "brain";
  prior: TestLadderPrior;
}

/** Output of the pure M4 engine, unchanged. Probabilities are intervals, never single numbers. */
export interface TestLadderResponse {
  as_of: string;
  facility_id: string;
  illustrative_facility: boolean;
  negative_result_excludes_involvement: boolean;
  negative_result_statement: string;
  notes: string[];
  organ: string;
  outcome: "ladder" | "refer" | "no_sourced_option";
  prior: Record<string, unknown>;
  referrals: Record<string, unknown>[];
  rungs: Record<string, unknown>[];
  scope_statement: string;
  skipped: Record<string, string>[];
}

export interface TrajectoryPoint {
  alt_level: number;
  alt_velocity_pct?: number | null;
  ast_level: number;
  ca153_velocity_pct?: number | null;
  ca_15_3: number;
  calculated_metastasis_risk: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  creatinine: number;
  date_drawn: string /* ISO 8601 */;
  justification_text: string;
  lab_id: string;
  triage_flag: boolean | null;
  wbc_count: number;
}

export interface TriageQueueItem {
  action_urgency: number | null;
  age: number;
  last_lab_date?: string /* ISO 8601 */ | null;
  latest_justification: string;
  latest_risk: number | null;
  patient_id: string;
  status: string;
  subtype?: string;
  target_organ_susceptibility_vector: Record<string, number> | null;
  total_labs?: number;
  triage_flag: boolean | null;
  tumor_stage?: number | null;
  urgency_breakdown: Record<string, number> | null;
}

export interface ValidationError {
  ctx?: Record<string, unknown>;
  input?: unknown;
  loc: string | number[];
  msg: string;
  type: string;
}
