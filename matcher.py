"""LLM-based job matching and scoring."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "profile.yaml"
JOBS_INPUT_CSV = ROOT / "web3_jobs.csv"
JOBS_SCORED_CSV = ROOT / "web3_jobs_scored.csv"

load_dotenv()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_JOBS_TO_SCORE = int(os.getenv("MAX_JOBS_TO_SCORE", "0") or 0)
JOBS_OFFSET = int(os.getenv("JOBS_OFFSET", "0") or 0)
INPUT_PATH = Path(os.getenv("INPUT_PATH", JOBS_INPUT_CSV))
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", JOBS_SCORED_CSV))
SCORE_FIELDS = [
    "match_score",
    "skill_match",
    "seniority_match",
    "domain_match",
    "preference_match",
    "match_points",
    "gaps",
    "recommendation",
    "reason_short",
]


def load_profile_text(path: Path) -> str:
    if not path.exists():
        return "Profile not provided."
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


def load_jobs(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def load_existing_scores(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        scores: Dict[str, Dict[str, Any]] = {}
        for row in reader:
            key = _job_key(row)
            scores[key] = {field: row.get(field, "") for field in SCORE_FIELDS}
        return scores


def _job_key(job: Dict[str, Any]) -> str:
    return "|".join(
        [
            job.get("source", "").strip(),
            job.get("external_id", "").strip() or job.get("url", "").strip(),
            job.get("title", "").strip(),
        ]
    )


def build_prompt(profile_text: str, job: Dict[str, str]) -> str:
    job_summary = f"""
<job_description>
Title: {job.get('title','')}
Company: {job.get('company','')}
Location: {job.get('location','')}
Remote: {job.get('remote','')}
Source: {job.get('source','')}
URL: {job.get('url','')}
Tags: {job.get('tags','')}
Description: {job.get('description','')}
</job_description>
"""
    profile_block = f"<candidate_profile>\n{profile_text}\n</candidate_profile>"
    scoring_instructions = """
You are a careful JSON-only scoring engine for job matching.
Candidate: junior Web3/crypto data/growth analyst, fluent in English and Chinese, also open to BD/partnerships/operations/community/growth and junior research roles in Web3 (including CN/HK/Greater China teams).
Two valid tracks:
- Track A: Data/analytics/BI/product analytics in Web3.
- Track B: BD/partnerships/ops/community/growth or junior research/crypto analyst roles in Web3.
Sub-scores (0-100):
- skill_match: overlap with data/growth/analytics or BD/ops/community/research skills relevant to Web3.
- seniority_match: how well seniority expectations match a junior/early-career profile (avoid roles demanding 7-10y director-level).
- domain_match: Web3/crypto/blockchain relevance (higher if clearly Web3/crypto).
- preference_match: fit on remote/location/company language (Chinese/English) if mentioned.
Overall match_score: weight skill_match and domain_match more; range 0-100.
Recommendation thresholds:
- must_apply: match_score >= 80 and gaps are minor.
- good_if_time: 65 <= match_score < 80.
- stretch: 50 <= match_score < 65 but strong learning potential.
- skip: otherwise.
Return ONLY a JSON object with fields:
{ "match_score": int, "skill_match": int, "seniority_match": int, "domain_match": int, "preference_match": int,
  "match_points": [..3-5..], "gaps": [..3-5..], "recommendation": "must_apply"|"good_if_time"|"stretch"|"skip",
  "reason_short": "one short sentence" }
"""
    return "\n".join([scoring_instructions, profile_block, job_summary])


def call_llm_for_job(profile_text: str, job: Dict[str, str]) -> Dict[str, Any]:
    prompt = build_prompt(profile_text, job)
    client = OpenAI()
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a careful JSON-only scoring engine for job matching."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {
            "match_score": 0,
            "skill_match": 0,
            "seniority_match": 0,
            "domain_match": 0,
            "preference_match": 0,
            "match_points": [],
            "gaps": [],
            "recommendation": "skip",
            "reason_short": "Failed to score",
        }


def score_jobs() -> None:
    profile_text = load_profile_text(PROFILE_PATH)
    jobs = load_jobs(INPUT_PATH)
    if not jobs:
        print("No jobs found to score.")
        return

    existing_scores = load_existing_scores(OUTPUT_PATH)

    if MAX_JOBS_TO_SCORE > 0:
        jobs_to_score = jobs[JOBS_OFFSET : JOBS_OFFSET + MAX_JOBS_TO_SCORE]
    else:
        jobs_to_score = jobs[JOBS_OFFSET:]
    print(f"Loaded {len(jobs)} jobs from {INPUT_PATH}")
    if JOBS_OFFSET:
        print(f"Starting from offset {JOBS_OFFSET}")
    print(f"Scoring {len(jobs_to_score)} jobs in this run")

    # score the requested slice and update existing scores map
    for job in tqdm(jobs_to_score, desc="Scoring jobs"):
        key = _job_key(job)
        result = call_llm_for_job(profile_text, job)
        existing_scores[key] = {
            "match_score": result.get("match_score", 0),
            "skill_match": result.get("skill_match", 0),
            "seniority_match": result.get("seniority_match", 0),
            "domain_match": result.get("domain_match", 0),
            "preference_match": result.get("preference_match", 0),
            "match_points": " | ".join(result.get("match_points", [])),
            "gaps": " | ".join(result.get("gaps", [])),
            "recommendation": result.get("recommendation", "skip"),
            "reason_short": result.get("reason_short", ""),
        }

    # merge all jobs with scores (preserve order of original jobs)
    scored_rows: List[Dict[str, Any]] = []
    for job in jobs:
        key = _job_key(job)
        merged = dict(job)
        if key in existing_scores:
            merged.update(existing_scores[key])
        scored_rows.append(merged)

    # fieldnames: union of job fields and score fields
    fieldnames: List[str] = []
    if scored_rows:
        for key in scored_rows[0].keys():
            fieldnames.append(key)
        for f in SCORE_FIELDS:
            if f not in fieldnames:
                fieldnames.append(f)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored_rows)
    print(f"Wrote scored jobs to {OUTPUT_PATH} ({len(scored_rows)} rows)")


if __name__ == "__main__":
    score_jobs()
