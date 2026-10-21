"""Unit tests for Module M3 (Plausibility Adjudicator) and Module M5 (Verified Narrative Engine)."""

from vigil_ml.m3 import adjudicate, rcv
from vigil_ml.m5 import (
    FORBIDDEN_PHRASES,
    generate_worked_journey,
    render_clinician_note,
    verify_narrative,
)


def test_m3_rcv_values():
    # CA 15-3: CVa ~ 0.05, CVi ~ 0.061 (E9)
    rcv_sym = rcv(0.05, 0.061, z=1.96, log_normal=False)
    assert 0.20 <= rcv_sym <= 0.25

    # CEA: CVa ~ 0.05, CVi ~ 0.127 (E9)
    rcv_cea_up, rcv_cea_down = rcv(0.05, 0.127, z=1.96, log_normal=True)
    assert rcv_cea_up > 0.35
    assert -0.40 <= rcv_cea_down <= -0.20


def test_m3_no_dismissal():
    # Outlier values should result in 'needs_repeat', never 'dismissed'
    history = [(0.0, 15.0), (90.0, 15.5), (180.0, 15.2)]
    res = adjudicate(history, 270.0, 150.0, cv_analytical=0.05, cv_within=0.10)
    assert res["action"] in {"needs_repeat", "escalate"}
    assert res["action"] != "dismissed"


def test_m5_worked_journeys():
    # Journey J2: Surprising spike adjudicated to repeat
    j2 = generate_worked_journey("j2_surprising_repeat")
    assert j2["adjudication"]["action"] == "needs_repeat"
    assert j2["verification"]["ok"] is True
    assert "gross-error probability" in j2["narrative"]

    # Journey: False alarm / benign biological fluctuation
    fa = generate_worked_journey("false_alarm_explained")
    assert fa["adjudication"]["action"] == "explained"
    assert fa["verification"]["ok"] is True
    assert "stable-component probability" in fa["narrative"]

    # Journey: Real progression
    rp = generate_worked_journey("real_progression_escalate")
    assert rp["adjudication"]["action"] == "escalate"
    assert rp["verification"]["ok"] is True
    assert "real-change probability" in rp["narrative"]


def test_m5_forbidden_claims_enforcement():
    facts = [
        {"type": "p_real", "value": 0.50},
        {"type": "p_error", "value": 0.05},
        {"type": "p_stable", "value": 0.45},
        {"type": "rcv", "value": 0.31},
        {"type": "observed_change", "value": 1.45},
        {"type": "action", "value": "needs_repeat"},
    ]
    base_note = render_clinician_note(facts)
    assert verify_narrative(base_note, facts)["ok"] is True

    for phrase in FORBIDDEN_PHRASES:
        tampered = f"{base_note} {phrase}."
        res = verify_narrative(tampered, facts)
        assert res["ok"] is False
        assert any("Forbidden claim" in v for v in res["violations"])


def test_m5_sub_narrative_monotonicity():
    facts = [
        {"type": "p_real", "value": 0.50},
        {"type": "p_error", "value": 0.05},
        {"type": "p_stable", "value": 0.45},
        {"type": "rcv", "value": 0.31},
        {"type": "observed_change", "value": 1.45},
        {"type": "action", "value": "needs_repeat"},
    ]
    note = render_clinician_note(facts)
    # Removing clauses or sentences should stay valid
    sentences = note.split(". ")
    shortened = ". ".join(sentences[:3]) + "."
    res = verify_narrative(shortened, facts)
    assert res["ok"] is True


def test_m5_adversarial_rejections():
    """Verify that verifier rejects diverse adversarial hallucinations, paraphrases, and extrapolations."""
    facts = [
        {"type": "p_real", "value": 0.50},
        {"type": "p_error", "value": 0.05},
        {"type": "p_stable", "value": 0.45},
        {"type": "rcv", "value": 0.31},
        {"type": "observed_change", "value": 1.45},
        {"type": "action", "value": "needs_repeat"},
    ]
    base_note = render_clinician_note(facts)
    assert verify_narrative(base_note, facts)["ok"] is True

    adversarial_cases = [
        # 1. Actionable diagnostic extrapolation / clinical hallucination
        "Recommend ordering an FDG-PET scan immediately to assess distant metastasis.",
        # 2. Subtle reassurance / conversational drift
        "The elevation is reassuringly mild and clinically insignificant.",
        # 3. Fabricated clinical finding
        "The patient has 3 new suspicious pulmonary nodules.",
        # 4. Sycophantic assistant filler
        "Based on comprehensive review of your oncology panel, here are the findings.",
        # 5. Inverted negation of verified fact
        "The calculated probability of true progression is not 50%.",
        # 6. Subtle single-word substitution
        "The calculated probability of false progression is 50%.",
        # 7. Altered units / nonsensical metric
        "The biological reference change value threshold is 31 ng/mL.",
    ]

    for adv in adversarial_cases:
        # Case alone
        res_solo = verify_narrative(adv, facts)
        assert res_solo["ok"] is False, f"Adversarial case accepted alone: {adv}"
        assert len(res_solo["violations"]) > 0

        # Appended to valid narrative
        res_appended = verify_narrative(f"{base_note} {adv}", facts)
        assert res_appended["ok"] is False, f"Adversarial case accepted when appended: {adv}"
        assert len(res_appended["violations"]) > 0

