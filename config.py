"""Environment-based settings for web3_job_collector."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_keywords(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "")
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


@dataclass
class Settings:
    output_path: str
    max_jobs_per_source: int
    filter_keywords_web3: List[str]
    filter_keywords_role: List[str]
    remoteok_tags: List[str]
    proxy: str | None
    verify_ssl: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            output_path=os.getenv("OUTPUT_PATH", "web3_jobs.csv"),
            max_jobs_per_source=int(os.getenv("MAX_JOBS_PER_SOURCE", "200")),
            filter_keywords_web3=_parse_keywords("FILTER_KEYWORDS_WEB3"),
            filter_keywords_role=_parse_keywords("FILTER_KEYWORDS_ROLE"),
            remoteok_tags=_parse_keywords("REMOTEOK_TAGS") or ["web3", "crypto", "blockchain", "defi", "nft", "dao"],
            proxy=os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("GLOBAL_PROXY") or None,
            verify_ssl=os.getenv("VERIFY_SSL", "true").lower() not in {"0", "false", "no"},
        )
