"""Fetcher for web3.career."""

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


class Web3CareerFetcher(BaseFetcher):
    def fetch(self, max_jobs: int) -> List[JobPosting]:
        resp = requests.get(self.url, timeout=30, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[JobPosting] = []

        cards = soup.select("tr.job-card") or soup.select("div.job-card") or soup.select("div[class*='job']")
        for card in cards:
            title_tag = card.select_one("a") or card.select_one("h2")
            company_tag = card.select_one("td.company") or card.select_one("span.company")
            location_tag = card.select_one("td.location") or card.select_one("span.location")
            meta = card.get_text(" ", strip=True)

            title = title_tag.get_text(strip=True) if title_tag else ""
            url = title_tag.get("href", "") if title_tag else self.url
            if url and url.startswith("/"):
                url = "https://web3.career" + url

            jobs.append(
                JobPosting(
                    source=self.source_name,
                    title=title,
                    company=(company_tag.get_text(strip=True) if company_tag else ""),
                    location=(location_tag.get_text(strip=True) if location_tag else "Remote"),
                    remote="remote" in meta.lower(),
                    seniority="",
                    employment_type="",
                    salary="",
                    posted_at="",
                    url=url,
                    tags=["web3", "career"],
                )
            )
            if len(jobs) >= max_jobs:
                break

        logger.info("web3.career fetched %d jobs", len(jobs))
        return jobs
