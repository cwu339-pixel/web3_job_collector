"""Web3 job sources and data model."""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


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


def _parse_datetime(value: Optional[object], fallback_epoch: Optional[float] = None) -> Optional[dt.datetime]:
    if hasattr(value, "tm_year"):
        try:
            return dt.datetime(value.tm_year, value.tm_mon, value.tm_mday, value.tm_hour, value.tm_min, value.tm_sec)
        except Exception:
            pass
    if isinstance(value, str):
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return dt.datetime.strptime(value, fmt)
            except Exception:
                continue
    if fallback_epoch:
        try:
            return dt.datetime.utcfromtimestamp(float(fallback_epoch))
        except Exception:
            return None
    return None


def _make_session(verify: bool, proxy: Optional[str]) -> requests.Session:
    sess = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    sess.mount("http://", HTTPAdapter(max_retries=retries))
    sess.mount("https://", HTTPAdapter(max_retries=retries))
    sess.headers.update({"User-Agent": USER_AGENT})
    if proxy:
        sess.proxies.update({"http": proxy, "https": proxy})
    sess.verify = verify
    return sess


def _get_soup(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:
        logger.warning("Request failed for %s (%s)", url, exc)
        return None


def fetch_web3_career(limit: int = 200, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    session = session or _make_session(True, None)
    page = 1
    while len(jobs) < limit:
        soup = _get_soup(session, f"https://web3.career/web3-jobs?page={page}")
        if not soup:
            break
        rows = soup.select("tr.table_row")
        if not rows:
            break
        for row in rows:
            title_tag = row.select_one("h2")
            company_tag = row.select_one("h3")
            time_tag = row.select_one("time")
            location_tag = (row.select("p") or [None])[0]
            tag_nodes = row.select("span.my-badge a")

            href = ""
            onclick = row.get("onclick", "")
            match = re.search(r"'([^']+)'", onclick)
            if match:
                href = match.group(1)
            if not href:
                anchor = row.select_one("a[data-turbo-frame='job']")
                href = anchor.get("href", "") if anchor else ""
            if href.startswith("/"):
                href = f"https://web3.career{href}"

            jobs.append(
                Job(
                    source="web3.career",
                    external_id=row.get("data-jobid") or href or (title_tag.get_text(strip=True) if title_tag else ""),
                    title=title_tag.get_text(strip=True) if title_tag else "",
                    company=company_tag.get_text(strip=True) if company_tag else "",
                    location=location_tag.get_text(strip=True) if location_tag else "Remote",
                    remote="remote" in (location_tag.get_text(strip=True).lower() if location_tag else "remote"),
                    url=href,
                    posted_at=_parse_datetime(time_tag.get("datetime")) if time_tag else None,
                    description=row.get_text(" ", strip=True),
                    tags=[tag.get_text(strip=True) for tag in tag_nodes],
                )
            )
            if len(jobs) >= limit:
                break
        page += 1
    logger.info("web3.career fetched %d jobs", len(jobs))
    return jobs


def fetch_crypto_jobs(limit: int = 200, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    session = session or _make_session(False, None)
    soup = _get_soup(session, "https://crypto.jobs/")
    if not soup:
        return jobs
    links = soup.select("a[href*='/jobs/']")
    seen: set[str] = set()
    for link in links:
        href = link.get("href", "")
        if "/jobs/" not in href:
            continue
        if href.startswith("/"):
            href = f"https://crypto.jobs{href}"
        if href in seen:
            continue
        seen.add(href)
        title = link.get_text(strip=True)
        if not title:
            continue
        parent_text = link.find_parent().get_text(" ", strip=True) if link.find_parent() else ""
        jobs.append(
            Job(
                source="crypto.jobs",
                external_id=href,
                title=title,
                company="",
                location="Remote",
                remote=True,
                url=href,
                posted_at=None,
                description=parent_text,
                tags=[],
            )
        )
        if len(jobs) >= limit:
            break
    logger.info("crypto.jobs fetched %d jobs", len(jobs))
    return jobs


def fetch_cryptocurrencyjobs(limit: int = 200, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    session = session or _make_session(False, None)
    soup = _get_soup(session, "https://cryptocurrencyjobs.co/remote")
    if not soup:
        return jobs
    cards = soup.select("a.card") or soup.select("article")
    for card in cards:
        title_tag = card.select_one("h2") or card.select_one("h3")
        company_tag = card.select_one(".company") or card.select_one("p")
        location_tag = card.select_one(".location") or card.select_one(".tag.location")
        href = card.get("href", "") or (card.select_one("a").get("href", "") if card.select_one("a") else "")
        if href.startswith("/"):
            href = f"https://cryptocurrencyjobs.co{href}"
        jobs.append(
            Job(
                source="cryptocurrencyjobs.co",
                external_id=href or (title_tag.get_text(strip=True) if title_tag else card.get_text(strip=True)[:64]),
                title=title_tag.get_text(strip=True) if title_tag else "",
                company=company_tag.get_text(strip=True) if company_tag else "",
                location=location_tag.get_text(strip=True) if location_tag else "Remote",
                remote="remote" in (location_tag.get_text(strip=True).lower() if location_tag else "remote"),
                url=href,
                posted_at=None,
                description=card.get_text(" ", strip=True),
                tags=[t.get_text(strip=True) for t in card.select(".tag")],
            )
        )
        if len(jobs) >= limit:
            break
    logger.info("cryptocurrencyjobs.co fetched %d jobs", len(jobs))
    return jobs


def fetch_cryptojobs_com(limit: int = 200, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    session = session or _make_session(False, None)
    soup = _get_soup(session, "http://cryptojobs.com/remote")
    if not soup:
        return jobs
    cards = soup.select("a[href*='/jobs/']")
    seen: set[str] = set()
    for card in cards:
        href = card.get("href", "")
        if "/jobs/" not in href:
            continue
        if href.startswith("/"):
            href = f"http://cryptojobs.com{href}"
        if href in seen:
            continue
        seen.add(href)
        title = card.get_text(strip=True)
        if not title:
            continue
        text = card.find_parent().get_text(" ", strip=True) if card.find_parent() else title
        jobs.append(
            Job(
                source="cryptojobs.com",
                external_id=href,
                title=title,
                company="",
                location="Remote",
                remote=True,
                url=href,
                posted_at=None,
                description=text,
                tags=[],
            )
        )
        if len(jobs) >= limit:
            break
    logger.info("cryptojobs.com fetched %d jobs", len(jobs))
    return jobs


def fetch_remote3(limit: int = 200, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    session = session or _make_session(False, None)
    soup = _get_soup(session, "https://remote3.co/remote-jobs")
    if not soup:
        return jobs
    cards = soup.select("a[href*='/remote-jobs/']") or soup.select("article")
    seen: set[str] = set()
    for card in cards:
        href = card.get("href", "")
        if "/remote-jobs" not in href:
            continue
        if href.startswith("/"):
            href = f"https://remote3.co{href}"
        if href in seen:
            continue
        seen.add(href)
        title = card.get_text(strip=True) or (card.select_one("h2").get_text(strip=True) if card.select_one("h2") else "")
        if not title:
            continue
        text = card.get_text(" ", strip=True)
        jobs.append(
            Job(
                source="remote3.co",
                external_id=href,
                title=title,
                company="",
                location="Remote",
                remote=True,
                url=href,
                posted_at=None,
                description=text,
                tags=[],
            )
        )
        if len(jobs) >= limit:
            break
    logger.info("remote3.co fetched %d jobs", len(jobs))
    return jobs


def fetch_remoteok_tags(tags: Sequence[str], limit_per_tag: int = 100, session: Optional[requests.Session] = None) -> List[Job]:
    jobs: List[Job] = []
    seen: set[str] = set()
    session = session or _make_session(True, None)
    tag_list = list(tags) if tags else ["web3"]
    for tag in tag_list:
        try:
            resp = session.get(
                f"https://remoteok.com/api?tag={tag}",
                timeout=30,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning("RemoteOK failed for tag %s (%s)", tag, exc)
            continue
        count = 0
        for entry in payload:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            external_id = str(entry.get("id"))
            if external_id in seen:
                continue
            seen.add(external_id)
            location = entry.get("location") or "Remote"
            url = entry.get("apply_url") or entry.get("url") or ""
            jobs.append(
                Job(
                    source="remoteok",
                    external_id=external_id,
                    title=entry.get("position", ""),
                    company=entry.get("company", ""),
                    location=location,
                    remote="remote" in location.lower(),
                    url=url,
                    posted_at=_parse_datetime(entry.get("date"), fallback_epoch=entry.get("epoch")),
                    description=entry.get("description", ""),
                    tags=[t for t in entry.get("tags", []) if t],
                )
            )
            count += 1
            if count >= limit_per_tag:
                break
    logger.info("RemoteOK fetched %d jobs across tags", len(jobs))
    return jobs


def fetch_all(
    limit_per_source: int = 200,
    remoteok_tags: Optional[Sequence[str]] = None,
    proxy: Optional[str] = None,
    verify_ssl: bool = True,
) -> List[Job]:
    base_session = _make_session(verify_ssl, proxy)
    lax_session = _make_session(False, proxy)
    sources: List[Tuple[str, Callable[[int], List[Job]]]] = [
        ("web3.career", lambda limit: fetch_web3_career(limit, session=base_session)),
        ("crypto.jobs", lambda limit: fetch_crypto_jobs(limit, session=lax_session)),
        ("cryptocurrencyjobs.co", lambda limit: fetch_cryptocurrencyjobs(limit, session=lax_session)),
        ("cryptojobs.com", lambda limit: fetch_cryptojobs_com(limit, session=lax_session)),
        ("remote3.co", lambda limit: fetch_remote3(limit, session=lax_session)),
        (
            "remoteok",
            lambda limit: fetch_remoteok_tags(
                remoteok_tags or ["web3", "crypto", "blockchain", "defi", "nft", "dao"],
                limit_per_tag=limit,
                session=base_session,
            ),
        ),
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

    logger.info("Total unique jobs collected: %d", len(all_jobs))
    return all_jobs
