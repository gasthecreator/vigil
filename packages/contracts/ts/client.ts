/**
 * Auto-generated API client for Vigil Precision Oncology Platform.
 * Generated from docs/api/openapi.json.
 */

import type * as Types from "./types";

export interface ClientConfig {
  baseUrl: string;
  authToken?: string;
  role?: string;
  userId?: string;
}

export class VigilApiClient {
  constructor(private config: ClientConfig) {}

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    if (this.config.authToken) headers.set("Authorization", `Bearer ${this.config.authToken}`);
    if (this.config.role) headers.set("X-Vigil-Role", this.config.role);
    if (this.config.userId) headers.set("X-Vigil-User-Id", this.config.userId);
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    const resp = await fetch(`${this.config.baseUrl}${path}`, { ...options, headers });
    if (!resp.ok) {
      const errorBody = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${errorBody}`);
    }
    return resp.json() as Promise<T>;
  }

  // Health & Root
  async getRoot(): Promise<Record<string, unknown>> {
    return this.request("/");
  }

  // Patients & Surveillance
  async listPatients(params?: { status?: string; mrn?: string }): Promise<Types.PatientResponse[]> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.mrn) query.set('mrn', params.mrn);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request(`/api/v1/patients/${qs}`);
  }

  async getPatient(patientId: string): Promise<Types.PatientResponse> {
    return this.request(`/api/v1/patients/${patientId}`);
  }

  async createPatient(patient: Types.PatientCreate): Promise<Types.PatientResponse> {
    return this.request("/api/v1/patients/", { method: "POST", body: JSON.stringify(patient) });
  }

  async updatePatient(patientId: string, update: Types.PatientUpdate): Promise<Types.PatientResponse> {
    return this.request(`/api/v1/patients/${patientId}`, { method: "PATCH", body: JSON.stringify(update) });
  }

  async grantConsent(patientId: string, consent: Types.ConsentCreateRequest): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/patients/${patientId}/consent`, { method: "POST", body: JSON.stringify(consent) });
  }

  async ingestObservation(patientId: string, obs: Types.ObservationCreateRequest): Promise<Types.ObservationCreateResponse> {
    return this.request(`/api/v1/patients/${patientId}/observations`, { method: "POST", body: JSON.stringify(obs) });
  }

  async listObservations(patientId: string): Promise<Record<string, any>[]> {
    return this.request(`/api/v1/patients/${patientId}/observations`);
  }

  async listRiskHistory(patientId: string): Promise<Types.RiskAssessmentSummary[]> {
    return this.request(`/api/v1/patients/${patientId}/risk-history`);
  }

  // Alerts
  async listAlerts(statusFilter = 'open'): Promise<Types.AlertSummary[]> {
    return this.request(`/api/v1/alerts/?status_filter=${statusFilter}`);
  }

  async acknowledgeAlert(alertId: string, ack: Types.AlertAcknowledgeRequest): Promise<Types.AlertAcknowledgeResponse> {
    return this.request(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST", body: JSON.stringify(ack) });
  }

  // Follow-Up Guardian (M6)
  async getOutreachList(params?: { facility_id?: string; simulated_now?: string }): Promise<Types.FollowUpTaskResponse[]> {
    const query = new URLSearchParams();
    if (params?.facility_id) query.set('facility_id', params.facility_id);
    if (params?.simulated_now) query.set('simulated_now', params.simulated_now);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request(`/api/v1/follow-up/outreach${qs}`);
  }

  async transitionFollowUpTask(taskId: string, req: Types.FollowUpTransitionRequest): Promise<Types.FollowUpTaskResponse> {
    return this.request(`/api/v1/follow-up/${taskId}/transition`, { method: "POST", body: JSON.stringify(req) });
  }

  // Offline Sync Replay
  async processSyncBatch(batch: Types.SyncBatchRequest): Promise<Types.SyncBatchResponse> {
    return this.request("/api/v1/sync/batch", { method: "POST", body: JSON.stringify(batch) });
  }

  // Audit Verification
  async verifyAuditChain(): Promise<{ valid: boolean; total_events: number; head_hash: string }> {
    return this.request("/api/v1/audit/verify");
  }

  // Family & Patient Companion (M8)
  async recordSymptom(patientId: string, symptom: Types.SymptomCreateRequest): Promise<Types.SymptomResponse> {
    return this.request(`/api/v1/patients/${patientId}/symptoms`, { method: "POST", body: JSON.stringify(symptom) });
  }

  async listSymptoms(patientId: string): Promise<Types.SymptomResponse[]> {
    return this.request(`/api/v1/patients/${patientId}/symptoms`);
  }

  async createCaregiverShare(patientId: string, share: Types.CaregiverShareCreateRequest): Promise<Types.CaregiverShareResponse> {
    return this.request(`/api/v1/patients/${patientId}/shares`, { method: "POST", body: JSON.stringify(share) });
  }

  async listCaregiverShares(patientId: string): Promise<Types.CaregiverShareResponse[]> {
    return this.request(`/api/v1/patients/${patientId}/shares`);
  }

  async revokeCaregiverShare(patientId: string, shareId: string): Promise<Types.CaregiverShareResponse> {
    return this.request(`/api/v1/patients/${patientId}/shares/${shareId}`, { method: "DELETE" });
  }

  async requestSecondLook(patientId: string, req: Types.SecondLookCreateRequest): Promise<Types.SecondLookResponse> {
    return this.request(`/api/v1/patients/${patientId}/second-look`, { method: "POST", body: JSON.stringify(req) });
  }

  async unlockDisclosure(patientId: string, req: Types.DisclosureUnlockRequest): Promise<Types.DisclosureUnlockResponse> {
    return this.request(`/api/v1/patients/${patientId}/disclosure/unlock`, { method: "POST", body: JSON.stringify(req) });
  }

  async getObservationExplainer(patientId: string, obsId: string): Promise<Types.PlainLanguageExplainerResponse> {
    return this.request(`/api/v1/patients/${patientId}/observations/${obsId}/explainer`);
  }

  async getCaregiverSharedSummary(shareToken: string): Promise<Record<string, any>> {
    return this.request(`/api/v1/companion/share/${shareToken}`);
  }

  async recordCaregiverSymptom(shareToken: string, symptom: Types.SymptomCreateRequest): Promise<Types.SymptomResponse> {
    return this.request(`/api/v1/companion/share/${shareToken}/symptoms`, { method: "POST", body: JSON.stringify(symptom) });
  }

  async getCaregiverObservationExplainer(shareToken: string, obsId: string): Promise<Types.PlainLanguageExplainerResponse> {
    return this.request(`/api/v1/companion/share/${shareToken}/observations/${obsId}/explainer`);
  }

  // Treatment Continuity & Radiotherapy (M7)
  async listLinacMachines(): Promise<Types.LinacMachineResponse[]> {
    return this.request("/api/v1/continuity/machines");
  }

  async updateMachineStatus(machineId: string, update: Types.LinacMachineStatusUpdate): Promise<Types.LinacMachineResponse> {
    return this.request(`/api/v1/continuity/machines/${machineId}/status`, { method: "POST", body: JSON.stringify(update) });
  }

  async listRadiotherapyCourses(params?: { patient_id?: string; course_status?: string }): Promise<Types.RadiotherapyCourseResponse[]> {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.course_status) query.set('course_status', params.course_status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request(`/api/v1/continuity/courses${qs}`);
  }

  async createRadiotherapyCourse(course: Types.RadiotherapyCourseCreate): Promise<Types.RadiotherapyCourseResponse> {
    return this.request("/api/v1/continuity/courses", { method: "POST", body: JSON.stringify(course) });
  }

  async solveSchedule(req: Types.ScheduleSolveRequest): Promise<Types.ScheduleSolveResponse> {
    return this.request("/api/v1/continuity/schedule/solve", { method: "POST", body: JSON.stringify(req) });
  }

  async confirmSchedule(req: Types.ScheduleConfirmRequest): Promise<Types.ScheduleConfirmResponse> {
    return this.request("/api/v1/continuity/schedule/confirm", { method: "POST", body: JSON.stringify(req) });
  }

  async getDelayLedger(params?: { patient_id?: string; course_id?: string }): Promise<Types.DelayLedgerEntryResponse[]> {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.course_id) query.set('course_id', params.course_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request(`/api/v1/continuity/ledger${qs}`);
  }

  async getPatientDelayNotice(patientId: string): Promise<Types.PatientDelayNoticeResponse> {
    return this.request(`/api/v1/continuity/patients/${patientId}/delay-notice`);
  }
}
