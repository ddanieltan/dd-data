# dd-data

> **Centralized Git-Scraping Repository** with strict Pydantic schema guards, automated workflow retries, and clean subfolder datasets.

Inspired by [Simon Willison's git-scraping pattern](https://simonwillison.net/series/git-scraping/), `dd-data` centralizes scraping logic, scheduling, data integrity guards, and versioned datasets into a single self-contained repository.

All scraped datasets are organized in the `data/` directory:
- `data/daily-weather/weather.json` (Daily air temperature readings)
- `data/hourly-rainfall/rainfall.json` (Real-time hourly rainfall readings)

---

## 🏗️ Architecture

```
                  ┌──────────────────────┐
                  │    dd-data (CI)      │
                  │  GitHub Actions Cron │
                  └──────────┬───────────┘
                             │
                     Fetch & Validate
                             │
                  ┌──────────▼───────────┐
                  │  Pydantic Guard      │
                  │  (Checks schema,     │
                  │   rejects bad data)  │
                  └──────────┬───────────┘
                             │
               Clean Normalized Data & Commit
                             │
                             ▼
                  ┌──────────────────────┐
                  │      data/...        │
                  │ (Committed directly) │
                  └──────────────────────┘
```

### Key Capabilities
1. **Zero External Secrets**: Commits directly to this repository in GitHub Actions using the built-in `GITHUB_TOKEN`. No Personal Access Tokens (PATs) or token expirations to manage!
2. **Schema Guards**: Responses are strictly validated using Pydantic models. Malformed responses, empty datasets, or HTTP 5xx errors immediately abort before writing to disk, ensuring bad data is never committed to git history.
3. **Transient Failure Resilience**: Workflows wrap the scraper execution in `nick-fields/retry@v3` (3 retry attempts) to absorb transient connection drops, timeouts, and rate limits.
4. **Deterministic Diffs**: Data is deterministically formatted with sorted keys and stable 2-space indentation. Commits are skipped entirely if data has not changed.

---

## 🚀 Local Development & CLI

### Prerequisites
- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv)

### Setup Environment
```bash
uv venv --python python3 .venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

### CLI Commands

#### 1. List all registered scrapers:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli list
```

#### 2. Dry-run a scraper locally:
Fetches live data from the API, validates against the Pydantic schema guard, and prints a preview without committing:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape daily-weather --dry-run
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape hourly-rainfall --dry-run
```

#### 3. Scrape and save to `data/` locally (without commit):
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape daily-weather --no-commit
```

#### 4. Validate an existing data file:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli validate daily-weather data/daily-weather/weather.json
```

### Running Tests
```bash
PYTHONPATH=src .venv/bin/pytest -v
```

---

## ➕ Adding a New Scraper

Adding a new dataset takes 3 simple steps:

### 1. Define the Scraper and Schema Guard
Create a new file in `src/dd_data/scrapers/my_scraper.py`:

```python
from typing import Any
import httpx
from pydantic import BaseModel, Field
from dd_data.core.base import BaseScraper, registry

class MyDataPayload(BaseModel):
    items: list[str] = Field(..., min_length=1)

@registry.register
class MyScraper(BaseScraper):
    name = "my-dataset"
    description = "Scrapes my new dataset"
    target_path = "data/my-dataset/latest.json"
    schema = MyDataPayload

    def fetch(self) -> Any:
        resp = httpx.get("https://api.example.com/data")
        resp.raise_for_status()
        return resp.json()
```

### 2. Export in Scrapers Init
Add the scraper to `src/dd_data/scrapers/__init__.py`:
```python
from dd_data.scrapers.my_scraper import MyScraper
```

### 3. Create a GitHub Actions Workflow
Add `.github/workflows/scrape-my-dataset.yml` with your desired cron frequency calling:
```yaml
PYTHONPATH=src uv run python -m dd_data.cli scrape my-dataset
```
