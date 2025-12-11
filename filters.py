"""Keyword-based filters for job relevance."""

from __future__ import annotations

from typing import Sequence

from sources import Job


def job_matches_keywords(job: Job, web3_keywords: Sequence[str], role_keywords: Sequence[str]) -> bool:
    """
    Returns True if the job looks like Web3/crypto AND matches the target role type.
    If a keyword list is empty, that layer is treated as "no filter".
    """
    text = " ".join(
        [
            job.title or "",
            job.description or "",
            job.location or "",
            " ".join(job.tags or []),
        ]
    ).lower()

    def any_keyword(keywords: Sequence[str]) -> bool:
        return any(k.lower() in text for k in keywords) if keywords else True

    is_web3 = any_keyword(web3_keywords)
    is_role = any_keyword(role_keywords)
    return is_web3 and is_role
