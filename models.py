"""Data models for job postings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class JobPosting:
    source: str
    title: str
    company: str
    location: str
    remote: bool
    seniority: str
    employment_type: str
    salary: str
    posted_at: str
    url: str
    tags: List[str] = field(default_factory=list)
