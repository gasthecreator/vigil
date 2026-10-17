#!/usr/bin/env python3
"""Export current FastAPI OpenAPI JSON schema.

Adheres to MASTER_PLAN.md §9.2 and WP5.5.
Writes formatted OpenAPI specification to docs/api/openapi.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add apps/api to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from vigil_api.main import app


def export_openapi(target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Exported OpenAPI spec with {len(schema.get('paths', {}))} paths to {target_path}")


def main() -> None:
    out = ROOT / "docs" / "api" / "openapi.json"
    export_openapi(out)


if __name__ == "__main__":
    main()
