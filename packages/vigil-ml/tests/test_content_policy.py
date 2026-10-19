from pathlib import Path

from vigil_ml.m5 import (
    FORBIDDEN_PHRASES,
    generate_worked_journey,
    render_clinician_note,
    render_plain_language_explainer,
    verify_narrative,
)

ROOT = Path(__file__).resolve().parents[3]
CONTENT_POLICY = (ROOT / "docs/design/CONTENT.md").read_text(encoding="utf-8").lower()


def test_plain_language_bands_match_the_policy_and_do_not_expose_numeric_risk():
    expected_bands = {
        "explained": "Normal biological fluctuation (routine monitoring)",
        "needs_repeat": "Analytical uncertainty (suspected lab or specimen variation)",
        "escalate": "Elevated signal (clinical team review recommended)",
    }
    for verdict, band in expected_bands.items():
        explainer = render_plain_language_explainer(verdict)
        assert explainer["verbal_band"] == band
        assert band.lower() in CONTENT_POLICY
        user_copy = " ".join(
            [explainer["headline"], explainer["verbal_band"], explainer["what_this_means"],
             explainer["recommended_action"], *explainer["questions_to_ask_your_doctor"]]
        )
        assert "%" not in user_copy
        assert "probability score" not in user_copy.lower()
        assert all(phrase not in user_copy.lower() for phrase in FORBIDDEN_PHRASES)


def test_m5_clinician_outputs_remain_fact_bound_and_policy_documents_negative_result_caveat():
    for journey_name in ("j2_surprising_repeat", "false_alarm_explained", "real_progression_escalate"):
        journey = generate_worked_journey(journey_name)
        note = render_clinician_note(journey["adjudication"]["rationale_facts"])
        assert verify_narrative(note, journey["adjudication"]["rationale_facts"])["ok"] is True
    assert "a negative result does not exclude involvement" in CONTENT_POLICY
