# Specification: dd-data (Centralized Git-Scraping Engine)

A centralized Git-Scraping repository named `dd-data` that manages scraping logic, scheduling, validation guards, and versioned datasets organized in `data/` subfolders.

---

## 1. Objectives & Principles

1. **Self-Contained Repository**: All scraping scripts, dependencies, Pydantic schemas, GitHub Actions cron schedules, and tracked data snapshots live in `dd-data`.
2. **Zero External Secrets**: Commits directly to this repository in GitHub Actions using the built-in `GITHUB_TOKEN`. No Personal Access Tokens (PATs) or token expirations to manage.
3. **Strict Data Integrity**: Every fetched payload must satisfy strict Pydantic models. Malformed, truncated, empty, or HTTP error payloads (e.g. `{"code": 500}`) abort execution with non-zero exit codes to prevent committing corrupt data into git history.
4. **Transient Resilience**: GitHub Actions workflows utilize step retries (`nick-fields/retry`) to absorb transient network drops, rate limits, or momentary upstream hiccups before failing fast.
5. **Deterministic Diffs**: Payloads are consistently normalized (sorted keys, stable 2-space indentation, trailing newlines) so git diffs only reflect genuine data changes. No empty commits are made when data hasn't changed.

---

## 2. Directory Layout

```text
dd-data/
├── .github/
│   └── workflows/
│       ├── scrape-daily-weather.yml
│       └── scrape-hourly-rainfall.yml
├── data/
│   ├── daily-weather/
│   │   └── weather.json
│   └── hourly-rainfall/
│       └── rainfall.json
├── src/
│   └── dd_data/
│       ├── __init__.py
│       ├── cli.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── base.py       # Scraper base class & registry
│       │   ├── git.py        # Safe Git diff checking & committing
│       │   └── logger.py     # Clean structured console logging
│       └── scrapers/
│           ├── __init__.py
│           ├── daily_weather.py
│           └── hourly_rainfall.py
├── tests/
│   ├── __init__.py
│   └── test_schemas.py
├── pyproject.toml
├── README.md
└── SPEC.md
```
