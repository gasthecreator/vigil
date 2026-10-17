/**
 * apps/web/src/lib/types.ts
 *
 * Re-exports strictly auto-generated contracts from packages/contracts.
 * Zero hand-written API entity types (Mandatory Phase 6a rule).
 */

export * from "@vigil/contracts";

export type ObservationItem = Record<string, any>;

/**
 * UI-Derived Triage View Model.
 * Derived at runtime from PatientResponse, RiskAssessmentSummary, and FollowUpTaskSummary.
 */
export interface TriagePatientViewModel {
  id: string;
  mrn?: string | null;
  age?: number | null;
  status: string;
  stage?: string | null;
  subtype?: string | null;
  compositeUrgencyScore: number;
  urgencyLevel: "urgent" | "high" | "medium" | "low";
  latestRisk?: number | null;
  latestRiskInterval?: [number, number] | null;
  latestAnalyteCode?: string | null;
  latestAnalyteValue?: number | null;
  latestAnalyteUnit?: string | null;
  latestM3Action?: "escalate" | "needs_repeat" | "explained" | null;
  latestM5Narrative?: string | null;
  openTasksCount: number;
  openAlertsCount: number;
  daysSinceLastVisit: number;
}
