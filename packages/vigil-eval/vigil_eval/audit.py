"""
vigil_eval.audit

Frozen Test Set Access Audit Logger.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §9.

Prevents test-set snooping, data dredging, and circular hyper-parameter optimization.
Records an immutable log of every access to frozen evaluation datasets.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class TestAccessRecord:
    timestamp: str
    dataset_name: str
    access_type: str  # e.g. "load_features", "benchmark_evaluation"
    caller: str
    purpose: str
    git_sha: Optional[str]
    num_samples: int
    is_frozen_test: bool = True


class FrozenTestAccessLogger:
    """Manages an append-only JSONL audit trail for frozen test set accesses."""

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            # Default to data/audit/frozen_test_access.jsonl in repo root
            root = Path(__file__).resolve().parent.parent.parent.parent
            self.log_path = root / "data" / "audit" / "frozen_test_access.jsonl"
        else:
            self.log_path = Path(log_path)

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_current_git_sha(self) -> Optional[str]:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            return res.stdout.strip() if res.returncode == 0 else None
        except Exception:
            return None

    def log_access(
        self,
        dataset_name: str,
        access_type: str,
        caller: str,
        purpose: str,
        num_samples: int,
    ) -> TestAccessRecord:
        """Appends an immutable access event to the frozen test log."""
        record = TestAccessRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            dataset_name=dataset_name,
            access_type=access_type,
            caller=caller,
            purpose=purpose,
            git_sha=self._get_current_git_sha(),
            num_samples=num_samples,
            is_frozen_test=True,
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

        return record

    def get_access_history(self, dataset_name: Optional[str] = None) -> list[Dict[str, Any]]:
        """Reads all access records from the audit trail."""
        if not self.log_path.exists():
            return []

        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if dataset_name is None or rec.get("dataset_name") == dataset_name:
                        records.append(rec)
        return records
