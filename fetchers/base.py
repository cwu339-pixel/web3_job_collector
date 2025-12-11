"""Base classes for job fetchers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from models import JobPosting


class BaseFetcher(ABC):
    def __init__(self, source_name: str, url: str) -> None:
        self.source_name = source_name
        self.url = url

    @abstractmethod
    def fetch(self, max_jobs: int) -> List[JobPosting]:
        raise NotImplementedError
