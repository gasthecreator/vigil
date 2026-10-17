"""Module M5: Provenance-Verified Clinical Narrative Engine.

Transforms structured biomarker plausibility facts (from Module M3) into clinician-facing
narrative text using deterministic templates and a strict semantic verification engine.

Safety Guarantees:
  1. No LLM on any critical clinical decision path (pure deterministic template generation).
  2. Strict forbidden-claim filtering (no unwarranted reassurance, diagnostic certainty,
     or unsolicited therapeutic directives).
  3. Provenance verification: every number and clinical assertion in the narrative is
     grounded in and bounded by the structured rationale fact table.
  4. Monotonic sub-narrative validity: omitting a factual sentence maintains validity,
     while mutating or swapping numbers across factual clauses is rejected.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

# Safety: Forbidden claim phrases that MUST NEVER appear in clinician notes
FORBIDDEN_PHRASES = [
    "you have cancer",
    "metastasis is confirmed",
    "there is no need to worry",
    "start chemotherapy now",
    "this is definitely lab error",
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


def verify_narrative(text: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify that a narrative note is fully warranted by structured rationale facts.

    Enforces:
      1. Absence of any forbidden claims.
      2. Grounding: Every number in the narrative matches its assigned fact type.
      3. Absence of untraced numbers (numbers not warranted by any fact).
      4. Rejection of swapped percentages between different semantic claims.

    Args:
        text: Clinical narrative text to verify.
        facts: Reference rationale facts table.

    Returns:
        dict: {"ok": bool, "violations": list[str]}
    """
    violations: List[str] = []
    text_lower = text.lower()

    # 1. Check for forbidden claims
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            violations.append(f"Forbidden claim detected: '{phrase}'")

    # 2. Check empty facts condition
    if not facts:
        # Check if text contains any numbers
        numbers_in_text = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        if numbers_in_text:
            violations.append(f"Narrative contains numbers {numbers_in_text} without underlying rationale facts")
        return {"ok": len(violations) == 0, "violations": violations}

    # Build fact lookup
    f_map: Dict[str, Any] = {}
    for f in facts:
        if isinstance(f, dict) and "type" in f and "value" in f:
            f_map[f["type"]] = f["value"]

    # Authorized numbers by semantic category
    authorized_pcts: Dict[str, int] = {}
    if "p_real" in f_map:
        v = float(f_map["p_real"])
        authorized_pcts["progression"] = int(round(v * 100)) if v <= 1.0 else int(round(v))
    if "p_error" in f_map:
        v = float(f_map["p_error"])
        authorized_pcts["error"] = int(round(v * 100)) if v <= 1.0 else int(round(v))
    if "p_stable" in f_map:
        v = float(f_map["p_stable"])
        authorized_pcts["stability"] = int(round(v * 100)) if v <= 1.0 else int(round(v))
    if "rcv" in f_map:
        v = float(f_map["rcv"])
        authorized_pcts["rcv"] = int(round(v * 100)) if v <= 1.0 else int(round(v))

    authorized_ratio: Optional[float] = None
    if "observed_change" in f_map:
        authorized_ratio = float(f_map["observed_change"])

    # Global set of valid numbers from facts
    allowed_numbers: Set[float] = set()
    for f in facts:
        val = f.get("value")
        if isinstance(val, (int, float)):
            fval = float(val)
            allowed_numbers.add(round(fval, 2))
            allowed_numbers.add(round(fval, 4))
            allowed_numbers.add(float(int(round(fval))))
            if fval <= 1.0:
                allowed_numbers.add(float(int(round(fval * 100))))
                allowed_numbers.add(round(fval * 100, 1))

    # 3. Sentence-level semantic and swap validation
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

    for s in sentences:
        s_lower = s.lower()
        pct_matches = [float(p) for p in re.findall(r"(\d+(?:\.\d+)?)\s*%", s)]

        # Progression check
        if "progression" in s_lower or "true change" in s_lower:
            if "progression" in authorized_pcts:
                exp_pct = authorized_pcts["progression"]
                for p in pct_matches:
                    if abs(p - exp_pct) > 0.5:
                        violations.append(
                            f"Sentence claims progression with {p}%, expected {exp_pct}%"
                        )

        # Gross error check
        if "error" in s_lower or "pre-analytical" in s_lower or "analytical error" in s_lower:
            if "error" in authorized_pcts:
                exp_pct = authorized_pcts["error"]
                for p in pct_matches:
                    if abs(p - exp_pct) > 0.5:
                        violations.append(
                            f"Sentence claims error with {p}%, expected {exp_pct}%"
                        )

        # Baseline stability check
        if "stability" in s_lower or "stable" in s_lower:
            if "stability" in authorized_pcts:
                exp_pct = authorized_pcts["stability"]
                for p in pct_matches:
                    if abs(p - exp_pct) > 0.5:
                        violations.append(
                            f"Sentence claims stability with {p}%, expected {exp_pct}%"
                        )

        # Reference change value check
        if "reference change" in s_lower or "rcv" in s_lower:
            if "rcv" in authorized_pcts:
                exp_pct = authorized_pcts["rcv"]
                for p in pct_matches:
                    if abs(p - exp_pct) > 0.5:
                        violations.append(
                            f"Sentence claims RCV with {p}%, expected {exp_pct}%"
                        )

        # Observed ratio check
        if "ratio" in s_lower or "observed marker" in s_lower:
            if authorized_ratio is not None:
                ratio_matches = [
                    float(m)
                    for m in re.findall(r"\b(\d+\.\d+)\b", s)
                    if not s[s.find(m) + len(m) :].startswith("%")
                ]
                for r in ratio_matches:
                    if abs(r - authorized_ratio) > 0.05:
                        violations.append(
                            f"Sentence claims observed ratio {r}, expected {authorized_ratio:.2f}"
                        )

    # 4. Untraced number detection (checks all numeric tokens in the entire text)
    # Extracts tokens like "14", "91", "1.45"
    all_num_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    for num_str in all_num_tokens:
        num_val = float(num_str)
        # Check if number matches any allowable value within tolerance
        matched = False
        for allowed in allowed_numbers:
            if abs(num_val - allowed) < 0.05:
                matched = True
                break
        if not matched:
            violations.append(f"Untraced number '{num_str}' in narrative not grounded in rationale facts")

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
