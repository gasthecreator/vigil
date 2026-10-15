"""The reality audit must catch each fabrication pattern (and pass honest code)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("reality_audit", ROOT / "scripts" / "reality_audit.py")
ra = importlib.util.module_from_spec(spec)
sys.modules["reality_audit"] = ra
spec.loader.exec_module(ra)

BAD = '''"""Module with phantom route (GhostEngineK1)."""
class M:
    def fit(self, X, y):
        self.is_fitted = True
        return self
    def run_sbc(self):
        return {"p": 0.5}
def run_study_s1():
    return {"auc": [0.652, 0.704, 0.741]}
'''

GOOD = '''"""Honest module."""
class M:
    def fit(self, X, y):
        self.coef_ = sum(y) / len(y)
        return self
    def run_sbc(self):
        return self.coef_
def run_study_s1(rows):
    return [r.auc for r in rows]
'''


def _scan(tmp_path, text):
    f = tmp_path / "m.py"
    f.write_text(text)
    return ra.scan_file(f, defined_classes=set())


def test_catches_all_patterns(tmp_path):
    out = "\n".join(_scan(tmp_path, BAD))
    for rule in ("[R1]", "[R2]", "[R3]", "[R4]"):
        assert rule in out, out


def test_passes_honest_code(tmp_path):
    assert _scan(tmp_path, GOOD) == []


def test_allow_marker(tmp_path):
    text = BAD.replace("def fit(self, X, y):", "def fit(self, X, y):  # reality: allow(R2) stateless rule")
    assert "[R2]" not in "\n".join(_scan(tmp_path, text))
