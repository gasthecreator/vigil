#!/usr/bin/env python3
"""Generate docs/api/openapi.json and docs/api/reference.md from the live FastAPI app (G-08).

uv run python scripts/generate_api_reference.py            # write both files
uv run python scripts/generate_api_reference.py --check    # fail if either committed file is stale
uv run python scripts/generate_api_reference.py --seed-fail  # doctor the committed schema; --check logic must fail
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

OUT_JSON = ROOT / "docs" / "api" / "openapi.json"
OUT_MD = ROOT / "docs" / "api" / "reference.md"
METHODS = ("get", "post", "put", "patch", "delete")
PUBLIC = {"/", "/health", "/live", "/ready"}


def build_json(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def build_markdown(schema: dict) -> str:
    info = schema.get("info", {})
    lines = [
        "# API reference",
        "",
        f"*Generated from the running app by `scripts/generate_api_reference.py` — {info.get('title', 'Vigil API')} "
        f"{info.get('version', '')}. Do not edit by hand; CI fails if it is stale.* "
        "Machine-readable schema: [`openapi.json`](openapi.json).",
        "",
        "Every route requires authentication unless marked **public**. `GET /metrics` needs "
        "`Authorization: Bearer $VIGIL_METRICS_TOKEN` and is disabled (403) when no token is set.",
        "",
    ]
    groups: dict[str, list[tuple[str, str, dict]]] = {}
    for path, ops in schema.get("paths", {}).items():
        for method in METHODS:
            op = ops.get(method)
            if op:
                groups.setdefault((op.get("tags") or ["untagged"])[0], []).append(
                    (path, method, op)
                )
    for tag in sorted(groups):
        lines += [
            f"## {tag}",
            "",
            "| Method | Path | Access | Summary | Responses |",
            "|---|---|---|---|---|",
        ]
        for path, method, op in sorted(groups[tag]):
            access = (
                "public"
                if (path in PUBLIC or path.startswith("/api/v1/companion/share/"))
                else ("token" if path == "/metrics" else "auth")
            )
            summary = (op.get("summary") or "").replace("|", "\\|")
            codes = ", ".join(sorted(op.get("responses", {})))
            lines.append(f"| {method.upper()} | `{path}` | {access} | {summary} | {codes} |")
        lines.append("")
    lines.append(f"*{sum(len(v) for v in groups.values())} operations.*")
    return "\n".join(lines) + "\n"


def stale(json_text: str, md_text: str, schema: dict) -> list[str]:
    out = []
    if json_text != build_json(schema):
        out.append("docs/api/openapi.json")
    if md_text != build_markdown(schema):
        out.append("docs/api/reference.md")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed-fail", action="store_true")
    args = ap.parse_args()

    from vigil_api.main import app

    schema = app.openapi()
    if args.check or args.seed_fail:
        json_text = OUT_JSON.read_text(encoding="utf-8") if OUT_JSON.exists() else ""
        md_text = OUT_MD.read_text(encoding="utf-8") if OUT_MD.exists() else ""
        if args.seed_fail:  # drop one committed path: the real comparison must notice
            doc = json.loads(json_text)
            doc["paths"].pop(next(iter(doc["paths"])))
            json_text = build_json(doc)
        bad = stale(json_text, md_text, schema)
        if bad:
            print(f"❌ stale (run scripts/generate_api_reference.py): {bad}", file=sys.stderr)
            return 1
        print("✅ API reference is fresh")
        return 0
    OUT_JSON.write_text(build_json(schema), encoding="utf-8")
    OUT_MD.write_text(build_markdown(schema), encoding="utf-8")
    print(f"Wrote {OUT_JSON.name} and {OUT_MD.name} ({len(schema['paths'])} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
