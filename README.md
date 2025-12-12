# Web3 Job Collector

CLI tools to collect Web3/crypto job postings, normalize them to CSV, and score them against your profile with an LLM. Supports a global remote pipeline and a CN/HK-focused pipeline.

## Features
- Global remote sources (remoteok, web3.career, cryptojobs.com) → `web3_jobs.csv`
- CN/HK sources (JobsDB HK Web3, Cake Web3) → `cn_web3_jobs.csv`
- LLM-based matching (`matcher.py`) with JSON-only scoring, batching, and resume/profile context
- `.env`-driven configuration for inputs/outputs, batching, and API settings

## Project Structure
```
.
├── main.py            # Global fetch entrypoint → web3_jobs.csv
├── sources.py         # Global sources (remoteok, web3.career, cryptojobs.com)
├── cn_main.py         # CN/HK fetch entrypoint → cn_web3_jobs.csv
├── cn_sources.py      # CN/HK sources (JobsDB HK Web3, Cake Web3)
├── matcher.py         # LLM scoring for any CSV (configurable input/output)
├── filters.py         # Keyword matching helper
├── storage.py         # CSV writer utilities
├── config.py          # Env config loader
├── requirements.txt   # Python deps (requests, bs4, openai, pyyaml, dotenv)
├── .env.example       # Sample env (copy to .env and fill secrets)
├── candidate_profile.yaml # Your profile (not committed)
└── fetchers/          # Legacy fetchers (kept for reference)
```

## Setup
```bash
cd web3_job_collector
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your OpenAI key, paths, batching, etc.
```

## Usage
### Fetch global jobs
```bash
./.venv/bin/python main.py       # writes web3_jobs.csv
```

### Fetch CN/HK jobs
```bash
ENABLE_CN_SOURCES=true ./.venv/bin/python cn_main.py   # writes cn_web3_jobs.csv
```

### Score jobs with LLM (batching supported)
- Configure `.env` for the desired CSV:
  - Global: `INPUT_PATH=web3_jobs.csv`, `OUTPUT_PATH=web3_jobs_scored.csv`
  - CN/HK: `INPUT_PATH=cn_web3_jobs.csv`, `OUTPUT_PATH=cn_web3_jobs_scored.csv`
- Set batching (example: 20 at a time):
  - `MAX_JOBS_TO_SCORE=20`
  - `JOBS_OFFSET=0` (then 20, 40, … to cover all rows)
- Run:
```bash
./.venv/bin/python matcher.py
```
Each run merges scores into the same output CSV (no overwrite of previous batches).

## Configuration (key vars)
- Global fetch: `OUTPUT_PATH`, `MAX_JOBS_PER_SOURCE`, `REMOTEOK_TAGS`
- CN/HK fetch: `ENABLE_CN_SOURCES`, `CN_OUTPUT_PATH`, `CN_MAX_JOBS_PER_SOURCE`, `CAKE_WEB3_LOCATIONS`
- Matcher: `INPUT_PATH`, `OUTPUT_PATH`, `MAX_JOBS_TO_SCORE`, `JOBS_OFFSET`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`)

## Notes
- Do **not** commit `.env` or `candidate_profile.yaml`.
- CSV outputs are ignored by default.
- Scraping: uses simple `requests + BeautifulSoup` only; respects normal HTTP (no bypass/automation).

## Quick Git Commands
```bash
git status
git add <files>
git commit -m "Add CN/HK pipeline and docs"
git push -u origin main
```
