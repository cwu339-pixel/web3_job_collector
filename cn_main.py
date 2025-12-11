"""Entry point for CN/HK Web3 job collection."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

from cn_sources import fetch_all_cn
from storage import save_jobs_to_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


def main() -> None:
    output_path = os.getenv("CN_OUTPUT_PATH", "cn_web3_jobs.csv")
    max_jobs_per_source = int(os.getenv("CN_MAX_JOBS_PER_SOURCE", "200"))
    cake_locations = [loc.strip() for loc in os.getenv("CAKE_WEB3_LOCATIONS", "Hong Kong S.A.R").split(",") if loc.strip()]
    jobs = fetch_all_cn(limit_per_source=max_jobs_per_source, cake_locations=cake_locations)
    save_jobs_to_csv(jobs, output_path)
    logger.info("Saved CN/HK jobs to %s", output_path)


if __name__ == "__main__":
    if os.getenv("ENABLE_CN_SOURCES", "true").lower() in {"1", "true", "yes"}:
        main()
    else:
        logger.info("ENABLE_CN_SOURCES not set to true; skipping CN/HK fetch.")
