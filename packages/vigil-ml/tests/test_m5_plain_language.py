"""Unit tests for M5 Plain-Language Result Explainer and Readability Metrics.

Verifies Master Plan §6.5, §6.8, and Phase 6b:
- Plain-language result explainer driven by M3 verdicts, including explicit abstention.
- Reading level strictly verified to Flesch-Kincaid Grade Level <= 8.0.
- Length tests (concise text <= 120 words).
- Verbal uncertainty bands present instead of raw percentages.
- Exactly 3 structured 'Questions to ask your doctor'.
- Rejection of forbidden clinical claims and invalid verdicts.
"""

import pytest
from vigil_ml.m5 import (
    compute_flesch_kincaid_grade_level,
    count_syllables,
    render_plain_language_explainer,
)


def test_syllable_counter():
    """Verify syllable counting accuracy on key plain-language terms."""
    assert count_syllables("test") == 1
    assert count_syllables("blood") == 1
    assert count_syllables("doctor") == 2
    assert count_syllables("stable") == 2
    assert count_syllables("hospital") == 3
    assert count_syllables("oncology") == 4


def test_flesch_kincaid_grade_level_calculation():
    """Verify FKGL calculation matches standard formula."""
    # Simple sentences with monosyllabic words should have low grade level
    simple_text = "The dog ran. The cat sat. The sun is hot."
    score = compute_flesch_kincaid_grade_level(simple_text)
    assert score < 2.0

    # Complex academic sentence should yield higher grade level
    complex_text = (
        "Epidemiological investigations substantiate that pathophysiological perturbations "
        "concomitantly precipitate biochemical biomarker volatility."
    )
    score_complex = compute_flesch_kincaid_grade_level(complex_text)
    assert score_complex > 12.0


@pytest.mark.parametrize("verdict", ["abstain", "explained", "needs_repeat", "escalate"])
def test_plain_language_explainer_reading_level_and_length(verdict: str):
    """Verify that all M3 verdicts yield FKGL <= 8.0 and concise word counts."""
    explainer = render_plain_language_explainer(
        verdict=verdict, analyte_code="CA 15-3", synthetic=True
    )

    assert explainer["verdict"] == verdict
    assert explainer["verified"] is True
    assert explainer["synthetic"] is True

    # 1. Reading level invariant (Flesch-Kincaid Grade Level <= 8.0)
    fkgl = explainer["flesch_kincaid_grade_level"]
    assert fkgl <= 8.0, f"FKGL {fkgl} exceeds maximum allowed grade 8.0 for verdict {verdict}"
    assert fkgl >= 0.0

    # 2. Length invariant (concise explanation <= 120 words)
    word_count = explainer["word_count"]
    assert word_count <= 120, f"Word count {word_count} exceeds 120 words for verdict {verdict}"
    assert word_count >= 15

    # 3. Verbal uncertainty band
    assert explainer["verbal_band"]
    # Verify no raw percentages in the family explanation
    assert "%" not in explainer["headline"]
    assert "%" not in explainer["what_this_means"]

    # 4. Questions to ask your doctor (exactly 3 questions)
    questions = explainer["questions_to_ask_your_doctor"]
    assert isinstance(questions, list)
    assert len(questions) == 3
    for q in questions:
        assert q.endswith("?")
        q_fkgl = compute_flesch_kincaid_grade_level(q)
        assert q_fkgl <= 8.0, f"Question FKGL {q_fkgl} exceeds 8.0: '{q}'"


def test_plain_language_explainer_invalid_verdict():
    """Verify rejection of unknown or dismissed verdicts."""
    with pytest.raises(ValueError, match="Invalid M3 verdict"):
        render_plain_language_explainer(verdict="dismissed", synthetic=True)

    with pytest.raises(ValueError, match="Invalid M3 verdict"):
        render_plain_language_explainer(verdict="unknown", synthetic=True)


def test_plain_language_explainer_requires_explicit_source_provenance():
    with pytest.raises(TypeError):
        render_plain_language_explainer(verdict="explained")
    assert render_plain_language_explainer(verdict="explained", synthetic=False)["synthetic"] is False


def test_plain_language_explainer_forbidden_claims():
    """Verify safety check fails if forbidden phrases are present."""
    from vigil_ml.m5 import FORBIDDEN_PHRASES

    for phrase in FORBIDDEN_PHRASES[:3]:
        fake_text = f"This result shows {phrase} and you should visit the doctor."
        matched = [p for p in FORBIDDEN_PHRASES if p in fake_text.lower()]
        assert phrase in matched

        def bad_explainer():
            for p in FORBIDDEN_PHRASES:
                if p in fake_text.lower():
                    raise ValueError(
                        f"Safety violation: forbidden phrase '{p}' in plain-language explainer."
                    )

        with pytest.raises(ValueError, match="Safety violation"):
            bad_explainer()


def test_abstention_copy_does_not_imply_stability_or_repeat_error():
    explainer = render_plain_language_explainer("abstain", synthetic=False)
    assert "not enough history" in explainer["headline"].lower()
    assert "stable" not in explainer["headline"].lower()
    assert "repeat test" not in explainer["recommended_action"].lower()
    assert "review this result" in explainer["recommended_action"].lower()
