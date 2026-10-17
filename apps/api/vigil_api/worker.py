"""Background Worker Service for Vigil Precision Oncology Platform.

Adheres to MASTER_PLAN.md §9.2, §9.4, and Phase 5 deliverables:
- Executes periodic reminder evaluation and outreach dispatch cycles.
- Resilient state handling with clean shutdown on SIGTERM / SIGINT.
- Transactional atomicity: tasks are processed with rollback on unhandled failure.
- Observable execution with structured logging and audit records.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from vigil_api.database import SessionLocal
from vigil_api.reminders import run_reminder_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [vigil-worker] %(message)s",
)
logger = logging.getLogger("vigil-worker")


class VigilWorker:
    """Resilient background worker process."""

    def __init__(self, interval_seconds: float = 1.0) -> None:
        self.interval_seconds = interval_seconds
        self.running = True
        self.total_cycles = 0
        self.total_receipts_processed = 0

        # Register OS signal handlers for graceful termination
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Optional[object]) -> None:
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}. Gracefully stopping worker...")
        self.running = False

    def run_cycle(self, db: Session, simulated_now: Optional[datetime] = None) -> int:
        """Run a single transactional evaluation cycle."""
        now = simulated_now or datetime.now(timezone.utc)
        try:
            receipts = run_reminder_cycle(db=db, current_time=now)
            count = len(receipts)
            self.total_receipts_processed += count
            self.total_cycles += 1
            if count > 0:
                logger.info(f"Cycle {self.total_cycles}: dispatched {count} reminders.")
            return count
        except Exception as e:
            logger.error(f"Error during worker cycle: {e}", exc_info=True)
            db.rollback()
            raise

    def start(self, once: bool = False, max_cycles: Optional[int] = None) -> None:
        """Start the worker execution loop."""
        logger.info(f"Vigil Worker started (interval: {self.interval_seconds}s, once: {once})")

        while self.running:
            db = SessionLocal()
            try:
                self.run_cycle(db)
            finally:
                db.close()

            if once:
                break
            if max_cycles and self.total_cycles >= max_cycles:
                break

            # Sleep in small increments to be responsive to termination signals
            sleep_step = 0.1
            elapsed = 0.0
            while self.running and elapsed < self.interval_seconds:
                time.sleep(sleep_step)
                elapsed += sleep_step

        logger.info(
            f"Vigil Worker shutdown complete. Cycles: {self.total_cycles}, "
            f"Total reminders dispatched: {self.total_receipts_processed}."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Vigil Background Worker")
    parser.add_argument("--interval", type=float, default=2.0, help="Loop interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument(
        "--max-cycles", type=int, default=None, help="Maximum number of cycles before exiting"
    )
    args = parser.parse_args()

    worker = VigilWorker(interval_seconds=args.interval)
    worker.start(once=args.once, max_cycles=args.max_cycles)


if __name__ == "__main__":
    main()
