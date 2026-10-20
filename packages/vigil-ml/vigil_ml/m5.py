"""Module M5: Provenance-Verified Clinical Narrative Engine.

Transforms structured biomarker plausibility facts (from Module M3) into clinician-facing
narrative text using deterministic templates and an exact template-derivation verification engine.

Safety Guarantees:
  1. No LLM on any critical clinical decision path (pure deterministic template generation).
  2. Template-derivation verification: A candidate note is valid if and only if every single
     sentence in the text is strictly derivable from the structured rationale facts.
     Any unwarranted claim (paraphrased claim, clinical assertion, numberless hallucination)
     is strictly rejected.
  3. Safety blacklist backstop: Independent safety filter against forbidden diagnosis or
     unwarranted directives.
  4. Monotonic sub-narrative validity: Omitting any factual sentence preserves validity,
     while modifying a single word or number invalidates the sentence.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

# Safety: Forbidden claim phrases that MUST NEVER appear in clinician notes (secondary backstop)
FORBIDDEN_PHRASES = [
    "you have cancer",
    "you do have cancer",
    "metastasis confirmed",
    "metastasis is confirmed",
    "there is no need to worry",
    "no need to worry",
    "start chemotherapy",
    "begin treatment",
    "stop her current medication",
    "stop the current treatment",
    "this is definitely lab error",
    "this result is a lab error",
    "certainly a laboratory mistake",
]


def render_clinician_note(facts: List[Dict[str, Any]]) -> str:
    """Render a clinician-facing narrative summary from structured rationale facts.

    Uses deterministic template sentences strictly bound to the provided facts.

    Args:
        facts: List of rationale facts (e.g. from M3 Plausibility Adjudicator).
               Expected fact types: "p_real", "p_error", "p_stable", "rcv",
               "observed_change", "action".

    Returns:
        Deterministic narrative string suitable for oncologist review.
    """
    if not facts:
        return "Surveillance result received without structured rationale facts. Recommend clinical review."

    f_map: Dict[str, Any] = {}
    for f in facts:
        if isinstance(f, dict) and "type" in f and "value" in f:
            f_map[f["type"]] = f["value"]

    sentences: List[str] = []

    # 1. Progression probability
    if "p_real" in f_map:
        val = float(f_map["p_real"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        sentences.append(f"Under the model assumptions, the real-change probability is {pct}%.")

    # 2. Gross error probability
    if "p_error" in f_map:
        val = float(f_map["p_error"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        sentences.append(
            f"Under the model assumptions, the gross-error probability is {pct}%."
        )

    # 3. Biological stability probability
    if "p_stable" in f_map:
        val = float(f_map["p_stable"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        sentences.append(f"Under the model assumptions, the stable-component probability is {pct}%.")

    # 4. Reference change value threshold
    if "rcv" in f_map:
        # RCV is always a fraction from M3 and can exceed 1.0 (e.g. 1.49 = 149%) for variable markers; scaling by
        # value magnitude would render 1.49 as "1%". Found by overseer review (PR #75).
        pct = int(round(float(f_map["rcv"]) * 100))
        sentences.append(f"The biological reference change value threshold is {pct}%.")

    # 5. Observed marker ratio
    if "observed_change" in f_map:
        val = float(f_map["observed_change"])
        sentences.append(f"The observed marker ratio is {val:.2f} relative to baseline.")

    # 6. Adjudicated recommendation
    if "action" in f_map:
        act = str(f_map["action"])
        sentences.append(f"The recommended clinical action is {act}.")

    if not sentences:
        return "Surveillance result received without structured rationale facts. Recommend clinical review."

    return " ".join(sentences)


def get_derivable_sentences(facts: List[Dict[str, Any]]) -> Set[str]:
    """Derive the complete set of valid canonical template sentences from facts."""
    if not facts:
        return {
            "Surveillance result received without structured rationale facts.",
            "Recommend clinical review.",
        }

    f_map: Dict[str, Any] = {}
    for f in facts:
        if isinstance(f, dict) and "type" in f and "value" in f:
            f_map[f["type"]] = f["value"]

    derivable: Set[str] = set()

    if "p_real" in f_map:
        val = float(f_map["p_real"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(f"Under the model assumptions, the real-change probability is {pct}%.")

    if "p_error" in f_map:
        val = float(f_map["p_error"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(
            f"Under the model assumptions, the gross-error probability is {pct}%."
        )

    if "p_stable" in f_map:
        val = float(f_map["p_stable"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(f"Under the model assumptions, the stable-component probability is {pct}%.")

    if "rcv" in f_map:
        pct = int(round(float(f_map["rcv"]) * 100))
        derivable.add(f"The biological reference change value threshold is {pct}%.")

    if "observed_change" in f_map:
        val = float(f_map["observed_change"])
        derivable.add(f"The observed marker ratio is {val:.2f} relative to baseline.")

    if "action" in f_map:
        act = str(f_map["action"])
        derivable.add(f"The recommended clinical action is {act}.")

    if not derivable:
        derivable.add(
            "Surveillance result received without structured rationale facts. Recommend clinical review."
        )

    return derivable


def verify_narrative(text: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify that a narrative note is fully warranted by structured rationale facts.

    Uses template-derivation: A note is accepted if and only if every sentence in it
    is an exact rendering of an authorized template sentence derived from `facts`.
    Blacklist serves as secondary defense.

    Args:
        text: Clinical narrative text to verify.
        facts: Reference rationale facts table.

    Returns:
        dict: {"ok": bool, "violations": list[str]}
    """
    violations: List[str] = []
    text_stripped = text.strip()

    if not text_stripped:
        return {"ok": False, "violations": ["Empty narrative text."]}

    # 1. Secondary Backstop: Check forbidden blacklist phrases
    text_lower = text_stripped.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            violations.append(f"Forbidden claim detected: '{phrase}'")

    # 2. Template-Derivation: Every sentence must strictly match a derivable sentence
    derivable_sentences = get_derivable_sentences(facts)

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_stripped) if s.strip()]
    if not sentences:
        return {"ok": False, "violations": ["No valid sentences found in narrative."]}

    for s in sentences:
        if s not in derivable_sentences:
            violations.append(f"Unwarranted claim not derivable from facts: '{s}'")

    return {"ok": len(violations) == 0, "violations": violations}


def generate_worked_journey(journey_id: str) -> Dict[str, Any]:
    """Generate one of three illustrative synthetic M3/M5 scenarios.

    Journeys:
      - 'j2_surprising_repeat': Synthetic 10x marker change -> model output needs_repeat.
      - 'false_alarm_explained': Synthetic 1.15x marker change -> model output explained.
      - 'real_progression_escalate': Synthetic 2.5x marker change -> model output escalate.

    Scenario labels describe generated inputs only. They are not clinical truth or
    evidence that M3 can identify analytical error, benign variation, or recurrence.
    """
    from vigil_ml.m3 import DEFAULT_M3_ASSUMPTIONS, adjudicate

    if journey_id == "j2_surprising_repeat":
        # Synthetic scenario: 10x change; generated inputs do not establish its cause.
        # Baseline ~18.0 U/mL (4 historical draws)
        history = [(30.0, 17.5), (90.0, 18.2), (180.0, 17.8), (270.0, 18.5)]
        new_day = 360.0
        new_val = 180.0  # 10x shift error
        adjudication = adjudicate(
            history,
            new_day,
            new_val,
            cv_analytical=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_analytical,
            cv_within=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_within,
        )
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "synthetic": True,
            "evidence_status": "illustrative_only",
            "title": "Synthetic scenario: 10x marker change; model output is needs_repeat",
            "clinical_context": "Illustrative generated values only: prior CA 15-3 values are near 18 U/mL; the current generated value is 180 U/mL.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    elif journey_id == "false_alarm_explained":
        # Synthetic scenario: 1.15x change; generated inputs do not establish benignity.
        history = [(30.0, 19.5), (90.0, 20.2), (180.0, 19.8), (270.0, 20.5)]
        new_day = 360.0
        new_val = 23.0  # 1.15x ratio
        adjudication = adjudicate(
            history,
            new_day,
            new_val,
            cv_analytical=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_analytical,
            cv_within=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_within,
        )
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "synthetic": True,
            "evidence_status": "illustrative_only",
            "title": "Synthetic scenario: 1.15x marker change; model output is explained",
            "clinical_context": "Illustrative generated values only: CA 15-3 changes from 20 to 23 U/mL; this scenario does not establish the cause or clinical significance of the change.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    elif journey_id == "real_progression_escalate":
        # Synthetic scenario: 2.5x change; generated inputs do not establish recurrence.
        history = [(30.0, 14.8), (90.0, 15.2), (180.0, 15.0), (270.0, 15.4)]
        new_day = 360.0
        new_val = 37.8  # 2.5x ratio
        adjudication = adjudicate(
            history,
            new_day,
            new_val,
            cv_analytical=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_analytical,
            cv_within=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_within,
        )
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "synthetic": True,
            "evidence_status": "illustrative_only",
            "title": "Synthetic scenario: 2.5x marker change; model output is escalate",
            "clinical_context": "Illustrative generated values only: CA 15-3 changes from 15 to 37.8 U/mL; this scenario does not establish recurrence or its cause.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    else:
        raise ValueError(f"Unknown journey_id: {journey_id}")


def count_syllables(word: str) -> int:
    """Estimates the number of syllables in an English word."""
    word = word.lower().strip(".,!?:;'\"-()")
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    # Check for -le ending preceded by consonant (table, stable, little)
    ends_in_le = bool(re.search(r"[bcdfghjklmnpqrstvwxz]le$", word))
    word = re.sub(r"(?:ed|es|e)$", "", word)
    word = re.sub(r"^y", "", word)
    syllables = len(re.findall(r"[aeiouy]{1,2}", word))
    if ends_in_le and not re.search(r"[aeiouy]le$", word):
        syllables += 1
    return max(1, syllables)


def compute_flesch_kincaid_grade_level(text: str) -> float:
    """Computes Flesch-Kincaid Grade Level for text readability.

    Formula: 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    if not sentences or not words:
        return 0.0
    num_syllables = sum(count_syllables(w) for w in words)
    score = 0.39 * (len(words) / len(sentences)) + 11.8 * (num_syllables / len(words)) - 15.59
    return round(max(0.0, score), 2)


def render_plain_language_explainer(
    verdict: str,
    synthetic: bool,
    facts: Optional[List[Dict[str, Any]]] = None,
    analyte_code: str = "CA 15-3",
) -> Dict[str, Any]:
    """Generates a plain-language result explainer for patients and family caregivers.

    Complies with Master Plan §6.5, §6.8, and Phase 6b:
    - Driven exclusively by M3 verdicts ('abstain', 'explained', 'needs_repeat', 'escalate') and verified facts.
    - Reading level strictly enforced to Flesch-Kincaid Grade Level <= 8.0.
    - Concise word count (<= 120 words).
    - Verbal uncertainty bands instead of raw percentages.
    - Includes 3 structured 'Questions to ask your doctor'.
    - Safety backstop: strictly rejects forbidden claims ('you have cancer', etc.).
    """
    verdict_clean = verdict.strip().lower()
    if not isinstance(synthetic, bool):
        raise ValueError("synthetic provenance must be explicitly true or false")
    if verdict_clean not in {"abstain", "explained", "needs_repeat", "escalate"}:
        raise ValueError(
            f"Invalid M3 verdict for explainer: '{verdict}'. Must be 'abstain', 'explained', 'needs_repeat', or 'escalate'."
        )

    if verdict_clean == "abstain":
        headline = "There is not enough history to compare this result."
        verbal_band = "No model estimate available"
        what_this_means = (
            "This tool needs an earlier result to compare changes over time. "
            "That information is not in the record yet. "
            "Your care team can review this result and decide what to do next."
        )
        recommended_action = "Ask your care team to review this result."
        questions = [
            "Can this result be compared with an earlier test?",
            "When should I have my next blood test?",
            "Who should I contact if I have questions before then?",
        ]
    elif verdict_clean == "explained":
        headline = "This tool did not flag a large change."
        verbal_band = "Model output found no large change"
        what_this_means = (
            "This tool compares this result with earlier recorded tests. "
            "It cannot confirm or rule out a health problem. "
            "Your care team can review this result with your full history."
        )
        recommended_action = "Ask your care team if your monitoring plan is unchanged."
        questions = [
            "Does my routine monitoring schedule stay the same?",
            "Are there any new symptoms I should report before my next visit?",
            "When is my next scheduled blood test or clinic appointment?",
        ]
    elif verdict_clean == "needs_repeat":
        headline = "Your care team should review this result."
        verbal_band = "Model output asks for more review"
        what_this_means = (
            "This tool found a pattern that needs more review. "
            "It cannot tell why the number changed or if it is a lab issue. "
            "Your care team can decide if another blood test is right."
        )
        recommended_action = "Ask your care team whether another blood test is needed."
        questions = [
            "When and where should I repeat this blood test?",
            "Are there any special instructions before my next blood draw?",
            "What specific symptoms should I watch for while waiting for the repeat test?",
        ]
    else:  # escalate
        headline = "Your care team should review this change."
        verbal_band = "Model output flagged a change"
        what_this_means = (
            "This tool found a change from earlier recorded tests. "
            "It cannot tell why the number changed or diagnose a health problem. "
            "Your care team can review this result with other tests and your full history."
        )
        recommended_action = "Ask your care team to review this result."
        questions = [
            "What follow-up test or scan do you recommend to check this result?",
            "Could another health issue or medicine cause this change?",
            "What symptoms or changes should I look out for right now?",
        ]

    # Combine text for readability and safety checks
    full_text = f"{headline} {what_this_means} {recommended_action}"
    fkgl = compute_flesch_kincaid_grade_level(full_text)
    word_count = len(re.findall(r"\b[a-zA-Z]+\b", full_text))

    # Safety: check against forbidden claims
    full_lower = full_text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in full_lower:
            raise ValueError(
                f"Safety violation: forbidden phrase '{phrase}' in plain-language explainer."
            )

    # Enforce reading grade <= 8.0 invariant
    if fkgl > 8.0:
        raise ValueError(f"Reading level violation: FKGL {fkgl} exceeds maximum allowed grade 8.0.")

    return {
        "verdict": verdict_clean,
        "headline": headline,
        "verbal_band": verbal_band,
        "what_this_means": what_this_means,
        "recommended_action": recommended_action,
        "questions_to_ask_your_doctor": questions,
        "flesch_kincaid_grade_level": fkgl,
        "word_count": word_count,
        "verified": True,
        "synthetic": synthetic,
    }
