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
  async createPatient(patient: Types.PatientCreate): Promise<Types.PatientSummary> {
    return this.request("/api/v1/patients/", { method: "POST", body: JSON.stringify(patient) });
  }

  async ingestObservation(patientId: string, obs: Types.ObservationCreateRequest): Promise<Types.ObservationCreateResponse> {
    return this.request(`/api/v1/patients/${patientId}/observations`, { method: "POST", body: JSON.stringify(obs) });
  }

  // Alerts
  async listAlerts(statusFilter = 'open'): Promise<Types.AlertSummary[]> {
    return this.request(`/api/v1/alerts/?status_filter=${statusFilter}`);
  }

  async acknowledgeAlert(alertId: string, ack: Types.AlertAcknowledgeRequest): Promise<Types.AlertAcknowledgeResponse> {
    return this.request(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST", body: JSON.stringify(ack) });
  }

  // Offline Sync Replay
  async processSyncBatch(batch: Types.SyncBatchRequest): Promise<Types.SyncBatchResponse> {
    return this.request("/api/v1/sync/batch", { method: "POST", body: JSON.stringify(batch) });
  }

  // Audit Verification
  async verifyAuditChain(): Promise<{ valid: boolean; total_events: number; head_hash: string }> {
    return this.request("/api/v1/audit/verify");
  }
}
