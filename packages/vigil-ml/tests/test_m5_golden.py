"""Exact-behaviour tests for M5 (written to kill surviving mutants; see reports/quality/MUTATION_SCORE.json).

Wording that patients and clinicians read is pinned to a reviewed golden file; arithmetic, verifier messages and
boundaries are asserted explicitly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from vigil_ml.m5 import (
    FORBIDDEN_PHRASES,
    compute_flesch_kincaid_grade_level,
    count_syllables,
    generate_worked_journey,
    get_derivable_sentences,
    render_clinician_note,
    render_plain_language_explainer,
    verify_narrative,
)

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "m5_golden.json").read_text(encoding="utf-8")
)
NO_FACTS = (
    "Surveillance result received without structured rationale facts. Recommend clinical review."
)


def _f(**kv):
    return [{"type": k, "value": v} for k, v in kv.items()]


# ---- clinician note -------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "facts, expected",
    [
        (_f(p_real=0.82), "The calculated probability of true progression is 82%."),
        (
            _f(p_error=0.07),
            "The calculated probability of analytical or pre-analytical error is 7%.",
        ),
        (_f(p_stable=0.5), "The calculated probability of baseline biological stability is 50%."),
        (_f(rcv=0.31), "The biological reference change value threshold is 31%."),
        (_f(rcv=1.49), "The biological reference change value threshold is 149%."),
        (_f(observed_change=2.5), "The observed marker ratio is 2.50 relative to baseline."),
        (_f(observed_change=1.154), "The observed marker ratio is 1.15 relative to baseline."),
        (_f(action="escalate"), "The recommended clinical action is escalate."),
        (_f(p_real=1.0), "The calculated probability of true progression is 100%."),
        (_f(p_real=0.0), "The calculated probability of true progression is 0%."),
        (
            _f(p_real=45),
            "The calculated probability of true progression is 45%.",
        ),  # legacy percent input
    ],
)
def test_each_fact_renders_its_exact_sentence(facts, expected):
    assert render_clinician_note(facts) == expected
    assert get_derivable_sentences(facts) == {expected}
    assert verify_narrative(expected, facts) == {"ok": True, "violations": []}


def test_sentence_order_and_joining_are_fixed():
    facts = _f(action="repeat", observed_change=2.0, rcv=0.3, p_stable=0.1, p_error=0.2, p_real=0.7)
    assert render_clinician_note(facts) == (
        "The calculated probability of true progression is 70%. "
        "The calculated probability of analytical or pre-analytical error is 20%. "
        "The calculated probability of baseline biological stability is 10%. "
        "The biological reference change value threshold is 30%. "
        "The observed marker ratio is 2.00 relative to baseline. "
        "The recommended clinical action is repeat."
    )


@pytest.mark.parametrize("facts", [[], [{"type": "p_real"}], [{"value": 1}], ["x"], _f(unknown=1)])
def test_missing_or_unusable_facts_give_the_fixed_fallback(facts):
    assert render_clinician_note(facts) == NO_FACTS


def test_fallback_is_derivable_and_verifies():
    assert get_derivable_sentences([]) == {
        "Surveillance result received without structured rationale facts.",
        "Recommend clinical review.",
    }
    assert get_derivable_sentences(_f(unknown=1)) == {NO_FACTS}
    assert verify_narrative(NO_FACTS, []) == {"ok": True, "violations": []}


def test_later_fact_of_same_type_wins():
    facts = [{"type": "p_real", "value": 0.1}, {"type": "p_real", "value": 0.9}]
    assert render_clinician_note(facts).endswith("is 90%.")


# ---- verifier -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_narrative_is_rejected_with_message(text):
    assert verify_narrative(text, _f(p_real=0.5)) == {
        "ok": False,
        "violations": ["Empty narrative text."],
    }


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_every_forbidden_phrase_is_flagged_case_insensitively(phrase):
    res = verify_narrative(f"Note: {phrase.upper()}.", _f(p_real=0.5))
    assert not res["ok"]
    assert f"Forbidden claim detected: '{phrase}'" in res["violations"]


def test_unwarranted_sentence_is_reported_verbatim_and_valid_ones_are_not():
    facts = _f(p_real=0.5)
    good = "The calculated probability of true progression is 50%."
    res = verify_narrative(good + " The tumour is shrinking.", facts)
    assert res == {
        "ok": False,
        "violations": ["Unwarranted claim not derivable from facts: 'The tumour is shrinking.'"],
    }


def test_changing_one_number_or_word_invalidates():
    facts = _f(p_real=0.5, action="escalate")
    assert not verify_narrative("The calculated probability of true progression is 51%.", facts)[
        "ok"
    ]
    assert not verify_narrative("The recommended clinical action is Escalate.", facts)["ok"]


def test_omitting_sentences_stays_valid_and_order_is_free():
    facts = _f(p_real=0.5, action="escalate")
    a = "The calculated probability of true progression is 50%."
    b = "The recommended clinical action is escalate."
    assert verify_narrative(b + " " + a, facts)["ok"]
    assert verify_narrative(a, facts)["ok"]


@pytest.mark.parametrize("sep", [" ", "  ", "\n"])
def test_sentences_split_on_whitespace_after_terminator(sep):
    facts = _f(p_real=0.5, action="escalate")
    t = (
        "The calculated probability of true progression is 50%."
        + sep
        + "The recommended clinical action is escalate."
    )
    assert verify_narrative(t, facts)["ok"]


def test_exclamation_and_question_terminate_sentences():
    res = verify_narrative("Bad claim! Another one? Third.", _f(p_real=0.5))
    assert res["violations"] == [
        "Unwarranted claim not derivable from facts: 'Bad claim!'",
        "Unwarranted claim not derivable from facts: 'Another one?'",
        "Unwarranted claim not derivable from facts: 'Third.'",
    ]


# ---- readability maths ----------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "word, n",
    [
        ("", 0),
        ("...", 0),
        ("a", 1),
        ("the", 1),
        ("cat", 1),
        ("test", 1),
        ("stable", 2),
        ("table", 2),
        ("little", 2),
        ("make", 1),
        ("blood", 1),
        ("routine", 2),
        ("changes", 1),
        ("monitoring", 4),
        ("yes", 1),
        ("year", 1),
        ("oncology", 4),
        ("looked", 1),
        ("Normal.", 2),
        ("(clinic)", 2),
    ],
)
def test_syllable_counts(word, n):
    assert count_syllables(word) == n


@pytest.mark.parametrize(
    "text, grade",
    [
        ("", 0.0),
        ("!!!", 0.0),
        ("Hi.", 0.0),
        ("The cat sat on the mat.", 0.0),
        ("Your oncology team will continue your regular monitoring plan.", 12.83),
        ("This blood test is higher. Please call us.", 0.0),
    ],
)
def test_flesch_kincaid_values(text, grade):
    assert compute_flesch_kincaid_grade_level(text) == grade


def test_flesch_kincaid_formula_and_floor_and_rounding():
    text = "Repeating the blood test gives your doctor an accurate and reliable picture."
    words = 12
    assert compute_flesch_kincaid_grade_level(text) == round(
        0.39 * (words / 1)
        + 11.8 * (sum(count_syllables(w) for w in text.rstrip(".").split()) / words)
        - 15.59,
        2,
    )


# ---- explainer + journeys (reviewed golden wording) ----------------------------------------------------------
@pytest.mark.parametrize("verdict", ["explained", "needs_repeat", "escalate"])
def test_explainer_matches_reviewed_golden_exactly(verdict):
    got = render_plain_language_explainer(verdict)
    assert got == GOLDEN["explainer"][verdict]
    assert got["verified"] is True and got["synthetic"] is True
    assert got["flesch_kincaid_grade_level"] <= 8.0
    full = f"{got['headline']} {got['what_this_means']} {got['recommended_action']}"
    assert got["word_count"] == len(re.findall(r"\b[a-zA-Z]+\b", full))


@pytest.mark.parametrize("raw", [" ESCALATE ", "Escalate", "\tescalate\n"])
def test_explainer_normalises_verdict(raw):
    assert render_plain_language_explainer(raw) == GOLDEN["explainer"]["escalate"]


@pytest.mark.parametrize("bad", ["", "unknown", "explain", "needs repeat"])
def test_explainer_rejects_unknown_verdict_with_message(bad):
    with pytest.raises(ValueError) as e:
        render_plain_language_explainer(bad)
    assert str(e.value) == (
        f"Invalid M3 verdict for explainer: '{bad}'. Must be 'explained', 'needs_repeat', or 'escalate'."
    )


def test_explainer_text_contains_no_forbidden_phrase_and_is_not_a_diagnosis():
    for v in ("explained", "needs_repeat", "escalate"):
        e = render_plain_language_explainer(v)
        blob = " ".join(
            [
                e["headline"],
                e["what_this_means"],
                e["recommended_action"],
                *e["questions_to_ask_your_doctor"],
            ]
        ).lower()
        assert not any(p in blob for p in FORBIDDEN_PHRASES)
        assert len(e["questions_to_ask_your_doctor"]) == 3


@pytest.mark.parametrize(
    "jid", ["j2_surprising_repeat", "false_alarm_explained", "real_progression_escalate"]
)
def test_worked_journeys_match_reviewed_golden(jid):
    got = generate_worked_journey(jid)
    assert got == GOLDEN["journeys"][jid]
    assert got["journey_id"] == jid
    assert got["verification"]["ok"] is True


def test_worked_journey_verdicts_are_the_documented_ones():
    verdicts = {j: generate_worked_journey(j)["adjudication"]["action"] for j in GOLDEN["journeys"]}
    assert verdicts == {
        "j2_surprising_repeat": "needs_repeat",
        "false_alarm_explained": "explained",
        "real_progression_escalate": "escalate",
    }


def test_unknown_journey_raises_with_id_in_message():
    with pytest.raises(ValueError, match="Unknown journey_id: nope"):
        generate_worked_journey("nope")
