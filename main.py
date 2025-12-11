"""CLI entry for collecting Web3 job postings."""

from __future__ import annotations

import logging
from collections import Counter

from config import Settings
from filters import job_matches_keywords
from sources import fetch_all
from storage import save_jobs_to_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_env()
    jobs = fetch_all(
        limit_per_source=settings.max_jobs_per_source,
        remoteok_tags=settings.remoteok_tags,
        proxy=settings.proxy,
        verify_ssl=settings.verify_ssl,
    )
    logger.info("Fetched %d raw jobs before keyword filtering", len(jobs))
    print(f"Raw jobs total (before keyword filtering): {len(jobs)}")
    print("By source:", Counter(job.source for job in jobs))

    filtered_jobs = [
        job
        for job in jobs
        if job_matches_keywords(job, settings.filter_keywords_web3, settings.filter_keywords_role)
    ]
    logger.info("%d jobs remain after Web3+role keyword filtering", len(filtered_jobs))
    print(f"After keyword filtering: {len(filtered_jobs)}")
    print("After filter by source:", Counter(job.source for job in filtered_jobs))

    save_jobs_to_csv(filtered_jobs, settings.output_path)
    logger.info("Saved jobs to %s", settings.output_path)


if __name__ == "__main__":
    main()
