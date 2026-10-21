# Patient and family explanation content policy

This policy applies to M5 patient/family explainers and all companion copy. It is a wording contract, not clinical validation.

## Uncertainty bands and numeric decision boundaries

M5 receives the M3 action and does not expose component probabilities to patients or caregivers. The M3 component values and decision thresholds are assumptions in a synthetic model, not calibrated clinical probabilities. `p_real` means the model's real-change component; it is not a recurrence probability. M3 chooses `needs_repeat` when the assumed gross-error posterior is at least 0.30, chooses `escalate` when the assumed real-change posterior is at least 0.60, and chooses `explained` only when the assumed stable-component posterior is at least 0.90. `needs_repeat` is also the conservative fallback when neither other rule is met.

| M3 output | Internal numeric condition | M5 verbal band | Required next step |
|---|---|---|---|
| `abstain` | no earlier valid observation is available | “No model estimate available” | Ask the care team to review the result |
| `explained` | assumed stable-component posterior ≥ 0.90, after earlier rules | “Model output found no large change” | Ask the care team whether the monitoring plan is unchanged |
| `needs_repeat` | assumed gross-error posterior ≥ 0.30, or conservative fallback | “Model output asks for more review” | Ask the care team whether another blood test is needed |
| `escalate` | assumed real-change posterior ≥ 0.60, unless the earlier error rule applies | “Model output flagged a change” | Ask the care team to review the result |

These implementation thresholds are not a clinical risk scale. No percentage, confidence interval, or frequency statement is shown to families unless separately validated and explicitly approved. The current text changes are drafts pending clinical review. Do not call a patient, scan, test, or cancer status normal.

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
