from __future__ import annotations

import argparse
import logging
import time

from app.database import SessionLocal
from app.ingestion.service import enqueue_due_refreshes, run_one_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim and process Sentellent ingestion jobs.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        with SessionLocal() as db:
            scheduled = enqueue_due_refreshes(db)
            job = run_one_job(db)
            if scheduled:
                logger.info("Queued %s stale followed ticker refresh(es)", scheduled)
            if job:
                logger.info("Processed job %s with status %s", job.id, job.status)
        if args.once:
            if job is None:
                return
            continue
        time.sleep(max(1, args.poll_seconds))


if __name__ == "__main__":
    main()
