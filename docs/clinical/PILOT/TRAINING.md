# Training materials for pilot staff

> **Status: DRAFT-UNREVIEWED.** Written from what the software does today (`apps/api`, `apps/web`). Not reviewed by a clinician, a trainer or a translator; not translated (see `docs/localization/` for review state). Nothing here has been used with real staff. A training session is not complete until a person records it in section 5.

## 1. What Vigil is and is not (read aloud at the start of every session)
- Vigil is decision support for follow-up after breast-cancer treatment. It looks at test results over time and says "this change looks real and needs a person's attention", "repeat the test", or "explained by the usual variation".
- It does **not** diagnose, does **not** say a patient is safe, and does **not** replace the follow-up visits and tests a patient is already due. "No alert" means only that this tool found nothing it can detect. Continue routine follow-up regardless.
- Everything it shows was produced by a model that has been tested on **simulated** patients and has not yet been validated on real patients. Use your judgement; you are never required to follow it.
- During **silent mode** it shows you nothing: results are recorded for later comparison only. If you see a risk score or alert from Vigil during a silent-mode period, that is an incident (section 6).

## 2. For clinicians
1. **Alerts need a recorded response.** An alert cannot be dismissed; acknowledging it requires one of: `confirmed_recurrence`, `false_alarm`, `sample_redraw_ordered`, `repeat_ordered`, `clinical_hold`, `other`, with a short reason. Record what you actually decided.
2. **"Needs repeat" is Vigil abstaining.** When it asks for a repeat, the value may be a measurement problem (wrong tube, wrong unit, haemolysis). Check the sample before treating the number as a change.
3. **Read the explanation, then the numbers.** An explanation is meant to cite only values that are in the record. If a number in the explanation does not match the chart, report it (section 6); do not act on the text.
4. **Bad news.** Escalate-level results are not shown to the patient or caregiver until a clinician releases them (`disclosure/unlock`). Before you release, make sure you can have the conversation. A patient or caregiver can *request* release; that creates a pending `disclosure_release_request` task (due in one day) and does not release anything. If a patient says they saw a result you have not released, stop and report immediately (stop rule S-02).
5. **Every action is audited.** Acknowledgements, releases and overrides are recorded with your identity.
6. **Radiotherapy queue ordering** is an explainable urgency ranking; any optimiser shown is badged "unvalidated in simulation" and must be confirmed by a person.

## 3. For nurses, clerks and data-entry staff
1. Enter the unit shown on the lab report exactly. If the system rejects a value (wrong unit, impossible value), **do not "fix" the number to make it pass**; re-read the report, and if the report itself is unusual, ask the laboratory.
2. Enter the date and time the specimen was **collected**, not the date it was entered.
3. Check the patient's name and id on the lab slip against the screen before saving.
4. You cannot release bad news to a patient. If a patient asks about their results, refer them to the clinician.
5. Consent: if the screen says consent is withdrawn, stop; do not use the paper chart to enter around it.
6. If the system is unavailable, carry on with the existing paper or local process and enter results afterwards with the true collection time.

## 4. What patients and caregivers are told (plain-language draft; needs clinical review, translation and reading-level testing)
> This programme helps your care team keep track of your test results over time. A computer program looks for changes that might need attention and tells your care team. It does not decide your treatment and it does not replace your appointments or tests. Please keep every appointment. If you feel unwell or notice anything worrying, contact your care team directly; do not wait for the program. Your care team decides what to share with you and when. You can ask to stop at any time and your care will not change.

## 5. Competency check (a trainer asks; the person answers; all must be correct)
| # | Question | Correct answer |
|---|---|---|
| 1 | The system shows no alert. What do you do? | Continue routine follow-up; no alert is not a statement of safety |
| 2 | A lab value is rejected as an impossible unit. | Re-read the report, check the unit, ask the laboratory; do not alter the number to pass |
| 3 | You want to close an alert you believe is a false alarm. | Acknowledge it with disposition `false_alarm` and a reason |
| 4 | The caregiver of a patient asks for the result that is waiting for release. | Refer to the clinician; the caregiver can request release, only a clinician can release |
| 5 | During a silent-mode period you see a Vigil score on a screen. | Stop, do not act on it, report as an incident |
| 6 | The explanation names a value that is not in the chart. | Do not act on the text; report it |
| 7 | The system is down. | Use the existing process; enter results later with true collection times |

Training record (one row per person; kept by the clinical lead; no patient information):
| Date | Role | Trainer | Questions 1-7 correct (yes/no) | Retrain date if no |
|---|---|---|---|---|
| | | | | |

## 6. Reporting a problem
Tell the on-call operator the same day (name to be set in `STOP-RULES.md` section 4). Do not wait for a pattern. Use `INCIDENT-TEMPLATE.md`. No blame: a report is how the controls get better.
