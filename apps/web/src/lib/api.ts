/**
 * apps/web/src/lib/api.ts
 *
 * Clinician Workstation API Client consuming generated VigilApiClient from @vigil/contracts.
 * Features:
 * - Direct delegation to generated VigilApiClient methods (no custom schema wrappers)
 * - Offline mutation queue (localStorage) with automatic sync replay via /api/v1/sync/batch
 * - Error propagation and role-header management (X-Vigil-Role: clinician)
 */

import {
  VigilApiClient,
  PatientCreate,
  PatientResponse,
  PatientUpdate,
  ObservationCreateRequest,
  ObservationCreateResponse,
  RiskAssessmentSummary,
  AlertSummary,
  AlertAcknowledgeRequest,
  AlertAcknowledgeResponse,
  FollowUpTaskResponse,
  FollowUpTaskSummary,
  FollowUpTransitionRequest,
  ConsentCreateRequest,
  SyncBatchRequest,
  SyncBatchResponse,
} from "@vigil/contracts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const apiClient = new VigilApiClient({
  baseUrl: API_BASE,
  role: "clinician",
  userId: "USR-CLINICIAN-01",
});

export const qualityApiClient = new VigilApiClient({
  baseUrl: API_BASE,
  role: "quality_lead",
  userId: "USR-QL-01",
});

// Offline Sync Queue Storage
const OFFLINE_QUEUE_KEY = "vigil_offline_mutations";

export interface PendingMutation {
  client_mutation_id: string;
  entity_type: string;
  action: string;
  patient_id: string;
  client_updated_at: string;
  payload: Record<string, unknown>;
}

export function getOfflineQueue(): PendingMutation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function queueOfflineMutation(mutation: PendingMutation): void {
  if (typeof window === "undefined") return;
  const current = getOfflineQueue();
  current.push(mutation);
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(current));
}

export function clearOfflineQueue(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(OFFLINE_QUEUE_KEY);
}

/**
 * Replays all pending mutations through the transactional sync endpoint /api/v1/sync/batch
 */
export async function flushOfflineSyncQueue(): Promise<SyncBatchResponse | null> {
  const queue = getOfflineQueue();
  if (queue.length === 0) return null;

  const batch: SyncBatchRequest = {
    client_timestamp: new Date().toISOString(),
    mutations: queue.map((m) => ({
      action: m.action,
      client_mutation_id: m.client_mutation_id,
      client_updated_at: m.client_updated_at,
      entity_type: m.entity_type,
      patient_id: m.patient_id,
      payload: m.payload,
    })),
    sync_id: `sync-${Date.now()}`,
  };

  try {
    const result = await apiClient.processSyncBatch(batch);
    clearOfflineQueue();
    return result;
  } catch (err) {
    console.error("Offline sync batch failed:", err);
    throw err;
  }
}
