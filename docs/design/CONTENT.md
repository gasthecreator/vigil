# Patient and family explanation content policy

This policy applies to M5 patient/family explainers and all companion copy. It is a wording contract, not clinical validation.

## Uncertainty bands and numeric decision boundaries

M5 receives the M3 action and does not expose the component probabilities to patients or caregivers. M3 currently chooses `needs_repeat` when the model's gross-error posterior is at least 0.30, chooses `escalate` when the progression posterior is at least 0.60, and chooses `explained` only when the stability posterior is at least 0.90. Because `needs_repeat` is also the conservative fallback when neither other rule is met, these boundaries are not a calibrated recurrence-risk scale and must not be rendered as personal cancer probabilities.

| M3 output | Internal numeric condition | M5 verbal band | Required next step |
|---|---|---|---|
| `explained` | stability posterior ≥ 0.90, after earlier rules | “Normal biological fluctuation (routine monitoring)” | Continue the existing schedule; report new symptoms |
| `needs_repeat` | gross-error posterior ≥ 0.30, or conservative fallback | “Analytical uncertainty (suspected lab or specimen variation)” | Repeat or review with the care team; a single result is not a diagnosis |
| `escalate` | progression posterior ≥ 0.60, unless the earlier error rule applies | “Elevated signal (clinical team review recommended)” | Contact the clinic for clinician review and the next step |

These are implementation thresholds in M3, not a clinical risk scale. No percentage, confidence interval, or frequency statement is shown to families unless a separately validated communication study and explicit product approval support it. The word “normal” is only permitted inside the exact M5 band above; never call a patient, scan, test, or cancer status normal.

## Forbidden wording

- A diagnosis or exclusion: “you have cancer”, “no cancer”, “metastasis confirmed”, “ruled out”.
- Reassurance from a low score: “safe”, “nothing to worry about”, “you are cancer-free”.
- Certainty about a cause: “this is definitely lab error”, “the result is certainly a mistake”.
- Unqualified probability, survival, or treatment-benefit claims in patient/family copy.
- A negative imaging result described as proof that disease is absent.

## What-to-do-next pattern

Every explanation states (1) what changed in plain words, (2) what remains uncertain, (3) who should review it, and (4) a concrete question to ask the clinic. A recommendation never orders a test, changes treatment, or replaces clinician judgement. M4 must include the literal safety statement: **“A negative result does not exclude involvement.”**

## Bad-news rules

Keep the established server-side disclosure gate. Do not bypass it in UI or speech. Use calm, short sentences; state uncertainty before action; do not put a severe interpretation in a notification preview. If disclosure is locked or M5 fails verification, show the existing locked/error state instead of generated substitute text. Read-aloud is user initiated, reads only visible verified explanation text, and degrades to a clear unsupported-browser message.
