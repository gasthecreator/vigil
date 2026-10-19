#!/usr/bin/env python3
"""scripts/run_demo.py

One-command synthetic demo for hospital walkthroughs (PROMPT-P15 Tier 3).

Seeds the same synthetic SQLite cohort used by e2e (`scripts/run_e2e_server.seed_database`),
starts the API on :8000 and the Next.js app on :3000, prints the owner script path and
journey URLs. Every patient row is `synthetic=true`; the UI shows the synthetic banner.

Usage
  make demo
  # or: uv run python scripts/run_demo.py
  # Ctrl-C stops both processes.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNER_SCRIPT = ROOT / "docs" / "demo" / "OWNER-SCRIPT.md"
DEMO_DB = ROOT / "data" / "demo_synthetic.db"


def _print_banner() -> None:
    print()
    print("=" * 72)
    print("  Vigil SYNTHETIC DEMO  —  research prototype, not a medical device")
    print("  Every seeded patient is tagged synthetic=true; UI shows the banner.")
    print("=" * 72)
    print()
    print("API:          http://127.0.0.1:8000/docs")
    print("Workstation:  http://127.0.0.1:3000/")
    print("  Patient:    http://127.0.0.1:3000/patients/PAT-001")
    print("  Continuity: http://127.0.0.1:3000/continuity")
    print("  Quality:    http://127.0.0.1:3000/quality")
    print("Companion:    http://127.0.0.1:3000/companion")
    print()
    print(f"Owner script: {OWNER_SCRIPT}")
    print("Stop with Ctrl-C.")
    print()


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "apps" / "api"))

    # Import after chdir so run_e2e_server env defaults apply, then override DB.
    import run_e2e_server  # noqa: E402

    os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DB}"
    run_e2e_server.seed_database(DEMO_DB)

    _print_banner()

    api_env = {
        **os.environ,
        "ENVIRONMENT": "local",
        "REQUIRE_AUTH": "false",
        "DATABASE_URL": f"sqlite:///{DEMO_DB}",
        "PYTHONPATH": os.pathsep.join(
            [
                str(ROOT / "apps" / "api"),
                str(ROOT / "packages" / "vigil-ml"),
                str(ROOT / "packages" / "vigil-core"),
                os.environ.get("PYTHONPATH", ""),
            ]
        ),
    }
    api = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import uvicorn; from vigil_api.main import app; "
            "uvicorn.run(app, host='127.0.0.1', port=8000, log_level='warning')",
        ],
        cwd=str(ROOT / "apps" / "api"),
        env=api_env,
    )
    web = subprocess.Popen(
        ["npm", "run", "dev", "--prefix", str(ROOT / "apps" / "web")],
        cwd=str(ROOT),
        env={**os.environ, "NEXT_PUBLIC_API_BASE_URL": "http://127.0.0.1:8000"},
    )

    stopping = False

    def _shutdown(_signum: int, _frame: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        print("\nShutting down demo…")
        for p in (web, api):
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in (web, api):
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    time.sleep(2)
    while True:
        if api.poll() is not None:
            print(f"API exited with code {api.returncode}", file=sys.stderr)
            _shutdown(signal.SIGTERM, None)
        if web.poll() is not None:
            print(f"Web exited with code {web.returncode}", file=sys.stderr)
            _shutdown(signal.SIGTERM, None)
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
