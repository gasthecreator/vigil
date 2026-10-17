/**
 * packages/ui/src/i18n/types.ts
 *
 * Types for multilingual localization support across Nigeria (en-NG, Pidgin, Yorùbá, Hausa, Igbo).
 * Per project instructions, all translations other than en-NG are explicitly marked "unreviewed".
 */

export type SupportedLocale = "en-NG" | "pcm" | "yo" | "ha" | "ig";

export interface LocaleMetadata {
  code: SupportedLocale;
  name: string;
  nativeName: string;
  isReviewed: boolean;
  unreviewedNotice?: string;
}

export interface TranslationDictionary {
  metadata: LocaleMetadata;
  common: {
    appName: string;
    syntheticBanner: string;
    syntheticDescription: string;
    loading: string;
    error: string;
    save: string;
    cancel: string;
    refresh: string;
    actions: string;
    unreviewedTranslationWarning: string;
  };
  triage: {
    title: string;
    subtitle: string;
    actionUrgency: string;
    highUrgency: string;
    mediumUrgency: string;
    lowUrgency: string;
    patientId: string;
    mrn: string;
    stageSubtype: string;
    lastObservation: string;
    openTasks: string;
    viewTimeline: string;
    emptyQueue: string;
  };
  adjudication: {
    panelTitle: string;
    adjudicationVerdict: string;
    explained: string;
    needsRepeat: string;
    escalate: string;
    neverDismissedPolicy: string;
    rationaleFacts: string;
    analyticalNoise: string;
    biologicalVariation: string;
    recommendedNextStep: string;
  };
  alerts: {
    inboxTitle: string;
    urgentCount: string;
    acknowledgeButton: string;
    acknowledgeModalTitle: string;
    dispositionPrompt: string;
    dispositionConfirmed: string;
    dispositionRepeatScheduled: string;
    dispositionEscalatedToImaging: string;
    notesPrompt: string;
    submitAcknowledgement: string;
  };
  followUp: {
    boardTitle: string;
    openTasksCount: string;
    reminderCascade: string;
    overdueDays: string;
    taskType: string;
    status: string;
    contactPatient: string;
    markCompleted: string;
  };
  intake: {
    drawerTitle: string;
    fastIntakeTip: string;
    analyteCode: string;
    value: string;
    unit: string;
    specimenDate: string;
    submitObservation: string;
    offlineSavedNotice: string;
  };
  companion: {
    title: string;
    subtitle: string;
    explainerTitle: string;
    secondLookTitle: string;
    symptomDiaryTitle: string;
    caregiverSharingTitle: string;
    badNewsModeTitle: string;
    badNewsWarning: string;
    unlockResults: string;
    emergencyNotice: string;
    disclaimer: string;
    requestSecondLook: string;
    logSymptom: string;
    voiceInput: string;
    listening: string;
    recordVoice: string;
    shareWithFamily: string;
    offlineSyncNotice: string;
  };
}
