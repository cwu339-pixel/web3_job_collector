"""Fetcher for CryptoJobsList."""

from __future__ import annotations

import logging
from typing import List

import requests
from bs4 import BeautifulSoup

from fetchers.base import BaseFetcher
from models import JobPosting

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


class CryptoJobsListFetcher(BaseFetcher):
    def fetch(self, max_jobs: int) -> List[JobPosting]:
        resp = requests.get(self.url, timeout=30, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[JobPosting] = []

        cards = soup.select("div.job-listing") or soup.select("div.card-job")
        for card in cards:
            title_tag = card.select_one("h3 a") or card.select_one("a.job-title")
            company_tag = card.select_one("p.company") or card.select_one("a.company")
            location_tag = card.select_one("span.location")
            tags = [t.get_text(strip=True) for t in card.select("span.badge")]

            title = title_tag.get_text(strip=True) if title_tag else ""
            url = title_tag.get("href", "") if title_tag else self.url
            if url and url.startswith("/"):
                url = "https://cryptojobslist.com" + url

            jobs.append(
                JobPosting(
                    source=self.source_name,
                    title=title,
                    company=(company_tag.get_text(strip=True) if company_tag else ""),
                    location=(location_tag.get_text(strip=True) if location_tag else "Remote"),
                    remote="remote" in (location_tag.get_text("", strip=True).lower() if location_tag else "remote"),
                    seniority="",
                    employment_type="",
                    salary="",
                    posted_at="",
                    url=url,
                    tags=tags,
                )
            )
            if len(jobs) >= max_jobs:
                break

        logger.info("cryptojobslist fetched %d jobs", len(jobs))
        return jobs
