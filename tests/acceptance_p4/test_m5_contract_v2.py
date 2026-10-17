"""Overseer-authored M5 acceptance tests, contract v2. DO NOT EDIT (see docs/ml/M3-M5-CONTRACT.md).

The v1 tests only used exact strings, which a keyword blacklist can pass. These tests check the real
requirement: a note may contain ONLY content warranted by the fact table. Anything else must be rejected,
including paraphrases of forbidden claims and claims that contain no numbers.
"""

from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("VIGIL_ACCEPT_P4") != "1":
    pytest.skip("set VIGIL_ACCEPT_P4=1 to run Phase 4 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
M5 = importlib.import_module(os.environ.get("VIGIL_M5_MODULE", "vigil_ml.m5"))
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""

UNWARRANTED = [
    # paraphrased forbidden claims
    "Metastasis confirmed.",
    "No need to worry.",
    "You do have cancer.",
    "The patient definitely has cancer.",
    "Start chemotherapy immediately.",
    "Begin treatment today.",
    "This result is a lab error.",
    "This is certainly a laboratory mistake.",
    # numberless clinical claims not present in the facts
    "The tumour is growing rapidly in the liver.",
    "The patient has liver involvement.",
    "Bone metastases are likely.",
    "Prognosis is poor.",
    "Surgery is recommended.",
    "The patient should stop her current medication.",
    "The disease has progressed.",
    "Imaging is not needed.",
    "Her condition is stable.",
]


def _facts(rng):
    pr, pe = float(rng.uniform(0.2, 0.7)), float(rng.uniform(0.01, 0.1))
    return [
        {"fact_id": "f1", "type": "p_real", "value": round(pr, 2)},
        {"fact_id": "f2", "type": "p_error", "value": round(pe, 2)},
        {"fact_id": "f3", "type": "p_stable", "value": round(1 - pr - pe, 2)},
        {"fact_id": "f4", "type": "rcv", "value": round(float(rng.uniform(0.2, 0.5)), 2)},
        {
            "fact_id": "f5",
            "type": "observed_change",
            "value": round(float(rng.uniform(1.1, 2.5)), 2),
        },
        {
            "fact_id": "f6",
            "type": "action",
            "value": str(rng.choice(["explained", "needs_repeat", "escalate"])),
        },
    ]


@pytest.mark.parametrize("sentence", UNWARRANTED)
def test_unwarranted_sentences_rejected(sentence):
    if "M5-VERIFY" in STUBS:
        pytest.xfail("M5-VERIFY registered as stub")
    facts = _facts(np.random.default_rng(7))
    note = M5.render_clinician_note(facts)
    assert M5.verify_narrative(note, facts)["ok"]
    assert not M5.verify_narrative(note + " " + sentence, facts)["ok"], (
        f"accepted unwarranted sentence: {sentence}"
    )
    # also when it replaces one of the real sentences, and when it stands alone
    parts = re.split(r"(?<=[.!?])\s+", note.strip())
    assert not M5.verify_narrative(" ".join(parts[:-1] + [sentence]), facts)["ok"]
    assert not M5.verify_narrative(sentence, facts)["ok"]


def test_every_sentence_must_be_derivable():
    """Any single sentence of the rendered note stays valid alone, but altering one word of it must not."""
    if "M5-VERIFY" in STUBS:
        pytest.xfail("M5-VERIFY registered as stub")
    facts = _facts(np.random.default_rng(8))
    note = M5.render_clinician_note(facts)
    for s in re.split(r"(?<=[.!?])\s+", note.strip()):
        assert M5.verify_narrative(s, facts)["ok"], f"genuine sentence rejected alone: {s}"
        words = s.split()
        k = next((i for i, w in enumerate(words) if re.fullmatch(r"[A-Za-z-]{5,}", w)), None)
        if k is None:
            continue
        altered = " ".join(words[:k] + ["definitely"] + words[k + 1 :])
        assert not M5.verify_narrative(altered, facts)["ok"], (
            f"altered sentence accepted: {altered}"
        )
