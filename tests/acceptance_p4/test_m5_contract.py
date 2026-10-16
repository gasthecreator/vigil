"""Overseer-authored M5 acceptance tests. DO NOT EDIT (see docs/ml/M3-M5-CONTRACT.md)."""

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

FORBIDDEN = [
    "You have cancer.",
    "Metastasis is confirmed.",
    "There is no need to worry.",
    "Start chemotherapy now.",
    "This is definitely lab error.",
]


def _gate(token):
    if token in STUBS:
        pytest.xfail(f"{token} registered as stub")


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


def test_round_trip_verifies():
    _gate("M5-VERIFY")
    rng = np.random.default_rng(1)
    for _ in range(200):
        facts = _facts(rng)
        note = M5.render_clinician_note(facts)
        res = M5.verify_narrative(note, facts)
        assert res["ok"], res["violations"]


def _note(seed):
    rng = np.random.default_rng(seed)
    for _ in range(50):
        facts = _facts(rng)
        note = M5.render_clinician_note(facts)
        if len(set(re.findall(r"\d+(?:\.\d+)?%", note))) >= 2:
            return facts, note
    pytest.fail("rendered notes never contain two distinct percentages; cannot test swaps")


def test_number_mutations_rejected():
    _gate("M5-VERIFY")
    facts, note = _note(2)
    pcts = list(dict.fromkeys(re.findall(r"\d+(?:\.\d+)?%", note)))
    other = "91%" if "91%" not in pcts else "93%"
    assert not M5.verify_narrative(note.replace(pcts[0], other, 1), facts)["ok"], (
        "changed number accepted"
    )
    swapped = note.replace(pcts[0], "@@A@@").replace(pcts[1], pcts[0]).replace("@@A@@", pcts[1])
    assert not M5.verify_narrative(swapped, facts)["ok"], "swapped numbers accepted"
    assert not M5.verify_narrative(note + " Expected delay is 14 days.", facts)["ok"], (
        "novel number accepted"
    )


@pytest.mark.parametrize("sentence", FORBIDDEN)
def test_forbidden_claims_rejected(sentence):
    _gate("M5-SAFETY")
    facts, note = _note(3)
    assert not M5.verify_narrative(note + " " + sentence, facts)["ok"], f"accepted: {sentence}"


def test_empty_facts_safe_and_removal_ok():
    _gate("M5-VERIFY")
    note = M5.render_clinician_note([])
    assert isinstance(note, str) and note.strip()
    assert M5.verify_narrative(note, [])["ok"]
    facts, full = _note(4)
    sentences = re.split(r"(?<=[.!?])\s+", full.strip())
    if len(sentences) >= 2:
        assert M5.verify_narrative(" ".join(sentences[:-1]), facts)["ok"], (
            "removing a sentence should stay valid"
        )
