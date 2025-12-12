"""Chinese / Hong Kong Web3 job sources (requests + BeautifulSoup only)."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)

JOBSDB_HK_WEB3_BASE = "https://hk.jobsdb.com/zh/web3-jobs"
CAKE_WEB3_BASE = "https://www.cake.me/jobs/Web3"


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    remote: bool
    url: str
    posted_at: Optional[dt.datetime]
    description: str
    tags: List[str] = field(default_factory=list)


def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    """Best-effort parsing for simple date strings found on CN/HK sites."""
    if not value:
        return None
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def _http_get(url: str) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        logger.warning("Request failed for %s (%s)", url, exc)
        return None


def _get_soup(url: str) -> Optional[BeautifulSoup]:
    resp = _http_get(url)
    if not resp:
        return None
    return BeautifulSoup(resp.text, "html.parser")


def _extract_jobsdb_cards(soup: BeautifulSoup) -> List[Job]:
    """Extract job cards from the JobsDB HK Web3 listing."""
    jobs: List[Job] = []
    cards = soup.select("article") or []
    for card in cards:
        title_tag = card.select_one("a[data-automation='jobTitle']") or card.select_one("a")
        company_tag = card.select_one("a[data-automation='jobCompany']") or card.select_one("span[data-automation='jobCompany']")
        location_tag = card.select_one("span[data-automation='jobLocation']")
        date_tag = card.select_one("span[data-automation='jobListingDate']") or card.select_one("span[class*='job-date']")
        desc_tag = card.select_one("div[data-automation='jobShortDescription']") or card.select_one("div")

        href = title_tag.get("href", "") if title_tag else ""
        if href and href.startswith("/"):
            href = f"https://hk.jobsdb.com{href}"
        external_id = href or (title_tag.get_text(strip=True) if title_tag else card.get_text(strip=True)[:64])

        jobs.append(
            Job(
                source="jobsdb_hk",
                external_id=external_id,
                title=title_tag.get_text(strip=True) if title_tag else "",
                company=company_tag.get_text(strip=True) if company_tag else "",
                location=location_tag.get_text(strip=True) if location_tag else "Hong Kong",
                remote="remote" in (location_tag.get_text(strip=True).lower() if location_tag else ""),
                url=href,
                posted_at=_parse_datetime(date_tag.get_text(strip=True) if date_tag else None),
                description=desc_tag.get_text(" ", strip=True) if desc_tag else card.get_text(" ", strip=True),
                tags=["web3"],
            )
        )
    return jobs


def fetch_jobsdb_hk_web3(limit: int = 200) -> List[Job]:
    """Fetch Web3 jobs from JobsDB HK Web3 listing with pagination."""
    jobs: List[Job] = []
    page = 1
    while len(jobs) < limit:
        url = JOBSDB_HK_WEB3_BASE if page == 1 else f"{JOBSDB_HK_WEB3_BASE}?page={page}"
        resp = _http_get(url)
        if not resp:
            break
        if resp.status_code == 404:  # type: ignore[union-attr]
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = _extract_jobsdb_cards(soup)
        if not cards:
            break
        for job in cards:
            jobs.append(job)
            if len(jobs) >= limit:
                break
        page += 1
    logger.info("jobsdb_hk fetched %d jobs", len(jobs))
    return jobs


def fetch_cake_web3(max_jobs: int = 200, locations: Optional[Sequence[str]] = None) -> List[Job]:
    """Fetch Web3 jobs from Cake for the provided locations."""
    jobs: List[Job] = []
    locations = locations or ["Hong Kong S.A.R"]
    for loc in locations:
        if len(jobs) >= max_jobs:
            break
        loc_param = loc.replace(" ", "+")
        url = f"{CAKE_WEB3_BASE}?locations%5B0%5D={loc_param}"
        soup = _get_soup(url)
        if not soup:
            continue
        cards = soup.select("a[href*='/jobs/']") or []
        seen_href: set[str] = set()
        for card in cards:
            href = card.get("href", "")
            if "/jobs/" not in href:
                continue
            if href.startswith("/"):
                href = f"https://www.cake.me{href}"
            if href in seen_href:
                continue
            seen_href.add(href)

            title = card.get_text(strip=True)
            if not title:
                continue
            parent_text = card.find_parent().get_text(" ", strip=True) if card.find_parent() else title
            jobs.append(
                Job(
                    source="cake_web3",
                    external_id=href,
                    title=title,
                    company="",
                    location=loc,
                    remote="remote" in loc.lower(),
                    url=href,
                    posted_at=None,
                    description=parent_text,
                    tags=["web3", loc],
                )
            )
            if len(jobs) >= max_jobs:
                break
    logger.info("cake_web3 fetched %d jobs", len(jobs))
    return jobs


def fetch_all_cn(limit_per_source: int = 200, cake_locations: Optional[Sequence[str]] = None) -> List[Job]:
    """Fetch all configured CN/HK sources and deduplicate."""
    sources: List[Tuple[str, Callable[[int], List[Job]]]] = [
        ("jobsdb_hk", fetch_jobsdb_hk_web3),
        ("cake_web3", lambda limit: fetch_cake_web3(limit, locations=cake_locations)),
    ]
    seen: set[Tuple[str, str]] = set()
    all_jobs: List[Job] = []

    for name, func in sources:
        try:
            jobs = func(limit_per_source)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", name, exc)
            continue

        new_jobs = []
        for job in jobs:
            key = (job.source, job.external_id)
            if key in seen:
                continue
            seen.add(key)
            new_jobs.append(job)
        logger.info("%s added %d jobs after dedupe", name, len(new_jobs))
        all_jobs.extend(new_jobs)

    logger.info("Total unique CN/HK jobs collected: %d", len(all_jobs))
    return all_jobs
