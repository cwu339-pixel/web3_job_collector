"""Persistence utilities for normalized jobs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from sources import Job


def save_jobs_to_csv(jobs: Iterable[Job], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    header = [
        "source",
        "external_id",
        "title",
        "company",
        "location",
        "remote",
        "url",
        "posted_at",
        "description",
        "tags",
    ]

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for job in jobs:
            writer.writerow(
                [
                    job.source,
                    job.external_id,
                    job.title,
                    job.company,
                    job.location,
                    "Yes" if job.remote else "No",
                    job.url,
                    job.posted_at.isoformat() if job.posted_at else "",
                    job.description,
                    ", ".join(job.tags),
                ]
            )
