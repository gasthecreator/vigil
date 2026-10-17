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
from typing import Any, Dict, List, Set

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
        sentences.append(f"The calculated probability of true progression is {pct}%.")

    # 2. Gross error probability
    if "p_error" in f_map:
        val = float(f_map["p_error"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        sentences.append(f"The calculated probability of analytical or pre-analytical error is {pct}%.")

    # 3. Biological stability probability
    if "p_stable" in f_map:
        val = float(f_map["p_stable"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        sentences.append(f"The calculated probability of baseline biological stability is {pct}%.")

    # 4. Reference change value threshold
    if "rcv" in f_map:
        val = float(f_map["rcv"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
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
        derivable.add(f"The calculated probability of true progression is {pct}%.")

    if "p_error" in f_map:
        val = float(f_map["p_error"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(f"The calculated probability of analytical or pre-analytical error is {pct}%.")

    if "p_stable" in f_map:
        val = float(f_map["p_stable"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(f"The calculated probability of baseline biological stability is {pct}%.")

    if "rcv" in f_map:
        val = float(f_map["rcv"])
        pct = int(round(val * 100)) if val <= 1.0 else int(round(val))
        derivable.add(f"The biological reference change value threshold is {pct}%.")

    if "observed_change" in f_map:
        val = float(f_map["observed_change"])
        derivable.add(f"The observed marker ratio is {val:.2f} relative to baseline.")

    if "action" in f_map:
        act = str(f_map["action"])
        derivable.add(f"The recommended clinical action is {act}.")

    if not derivable:
        derivable.add("Surveillance result received without structured rationale facts. Recommend clinical review.")

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
    """Generate one of three worked clinical journeys per Phase 4a requirements.

    Journeys:
      - 'j2_surprising_repeat': Surprising 10x spike (specimen error) -> adjudicate -> needs_repeat.
      - 'false_alarm_explained': Minor 1.15x fluctuation within biological RCV -> adjudicate -> explained.
      - 'real_progression_escalate': Persistent 2.5x surge above RCV -> adjudicate -> escalate.
    """
    from vigil_ml.m3 import adjudicate

    if journey_id == "j2_surprising_repeat":
        # Journey J2: Surprising result (decimal shift x10 transcription error)
        # Baseline ~18.0 U/mL (4 historical draws)
        history = [(30.0, 17.5), (90.0, 18.2), (180.0, 17.8), (270.0, 18.5)]
        new_day = 360.0
        new_val = 180.0  # 10x shift error
        adjudication = adjudicate(history, new_day, new_val, cv_analytical=0.05, cv_within=0.10)
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "title": "Journey J2: Surprising Marker Spike (Analytical Error) Adjudicated to Repeat",
            "clinical_context": "Patient on surveillance with stable CA 15-3 (~18 U/mL). Day 360 shows sudden jump to 180 U/mL.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    elif journey_id == "false_alarm_explained":
        # Benign biological fluctuation within RCV (1.15x increase, RCV is ~31%)
        history = [(30.0, 19.5), (90.0, 20.2), (180.0, 19.8), (270.0, 20.5)]
        new_day = 360.0
        new_val = 23.0  # 1.15x ratio
        adjudication = adjudicate(history, new_day, new_val, cv_analytical=0.05, cv_within=0.10)
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "title": "Benign Fluctuation: Biological Noise Within RCV Adjudicated as Explained",
            "clinical_context": "Patient on surveillance. CA 15-3 increases from 20 to 23 U/mL (1.15x), below RCV threshold.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    elif journey_id == "real_progression_escalate":
        # True disease recurrence (2.5x increase, well above RCV)
        history = [(30.0, 14.8), (90.0, 15.2), (180.0, 15.0), (270.0, 15.4)]
        new_day = 360.0
        new_val = 37.8  # 2.5x ratio
        adjudication = adjudicate(history, new_day, new_val, cv_analytical=0.05, cv_within=0.10)
        note = render_clinician_note(adjudication["rationale_facts"])
        verification = verify_narrative(note, adjudication["rationale_facts"])
        return {
            "journey_id": journey_id,
            "title": "True Recurrence: Biomarker Elevation Exceeding RCV Adjudicated to Escalate",
            "clinical_context": "Patient on surveillance. CA 15-3 surges from 15 to 37.8 U/mL (2.5x), exceeding RCV.",
            "adjudication": adjudication,
            "narrative": note,
            "verification": verification,
        }

    else:
        raise ValueError(f"Unknown journey_id: {journey_id}")
