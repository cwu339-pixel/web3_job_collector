# web3_job_collector

Simple pipeline that pulls Web3 job postings from multiple sources (RSS / JSON), filters by keywords, normalizes fields, and exports to CSV + Excel. Later you can wire it into cron, n8n, or GitHub Actions.

## Features
- `.env`-driven configuration via `python-dotenv`
- Placeholder sources list ready for you to swap in real Web3 job feeds
- Keyword filtering per job title/description
- Unified job schema saved to both CSV (`OUTPUT_CSV`) and Excel (`OUTPUT_XLSX`)

## Quick Start
```bash
cd web3_job_collector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env to set KEYWORDS, MAX_JOBS_PER_SOURCE, output paths, etc.
python main.py
```

## Configuration
- `KEYWORDS`: comma-separated list (default `web3,defi,crypto,blockchain`)
- `MAX_JOBS_PER_SOURCE`: cap requests per source (default 50)
- `OUTPUT_CSV` / `OUTPUT_XLSX`: output file paths

Replace the placeholder URLs in `sources.py` with actual feeds (e.g. crypto job boards). Each source can be RSS (parsed via `feedparser`) or JSON (fetched via `requests`).
