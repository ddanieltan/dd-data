# dd-data

> **Centralized Git-Scraping Engine** with strict Pydantic schema guards, automated workflow retries, and decoupled data repositories.

Inspired by [Simon Willison's git-scraping pattern](https://simonwillison.net/series/git-scraping/), `dd-data` centralizes scraping logic, dependency management, scheduling, and error handling into a single repository while pushing clean, versioned data commits to independent target repositories (such as [`ddanieltan/daily-weather-sg`](https://github.com/ddanieltan/daily-weather-sg) and [`ddanieltan/sg-hourly-rainfall`](https://github.com/ddanieltan/sg-hourly-rainfall)).

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
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
┌──────────────────┐                  ┌──────────────────┐
│ daily-weather-sg │                  │sg-hourly-rainfall│
│ (Target Repo)    │                  │  (Target Repo)   │
└──────────────────┘                  └──────────────────┘
```

### Key Capabilities
1. **Schema Guards**: Responses are strictly validated using Pydantic models. Malformed responses, empty datasets, or HTTP 5xx errors immediately abort before writing to disk, ensuring bad data is never committed to git history.
2. **Transient Failure Resilience**: Workflows wrap the scraper execution in `nick-fields/retry@v3` (3 retry attempts) to absorb transient connection drops, timeouts, and rate limits.
3. **No Dirty Diffs**: Data is deterministically formatted with sorted keys and stable 2-space indentation. Commits are skipped entirely if data has not changed.
4. **Decoupled Repositories**: Keeps individual data repositories lightweight, containing only data and commit logs, without redundant workflow boilerplate or scraping logic.

---

## ⚙️ Initial Setup

To allow `dd-data` to push updates into your individual data repositories:

1. Create a **Fine-Grained Personal Access Token** in GitHub:
   - Go to **GitHub Settings** > **Developer Settings** > **Personal Access Tokens** > **Fine-grained tokens**.
   - Set Repository Access to **Only select repositories**:
     - `ddanieltan/daily-weather-sg`
     - `ddanieltan/sg-hourly-rainfall`
     - *(Any future target data repositories)*
   - Grant Permissions:
     - **Repository permissions** > **Contents**: `Read and write`.
2. In the `dd-data` repository:
   - Go to **Settings** > **Secrets and variables** > **Actions**.
   - Create a repository secret named **`TARGET_REPO_PAT`** and paste your token.

---

## 🚀 Local Development & CLI

### Prerequisites
- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv)

### Setup Environment
```bash
uv venv --python python3 .venv
source .venv/bin/activate
uv pip install -e .  # or run via PYTHONPATH=src
```

### CLI Commands

#### 1. List all registered scrapers:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli list
```

#### 2. Dry-run a scraper locally:
Fetches live data from the API, validates against the Pydantic schema guard, and prints a preview without touching any git repository:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape daily-weather --dry-run
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape hourly-rainfall --dry-run
```

#### 3. Save validated output locally:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli scrape daily-weather -o /tmp/weather.json
```

#### 4. Validate an existing data file:
```bash
PYTHONPATH=src .venv/bin/python -m dd_data.cli validate daily-weather path/to/weather.json
```

### Running Tests
```bash
PYTHONPATH=src .venv/bin/pytest -v
```

---

## ➕ Adding a New Scraper

Adding a new dataset or target repository takes 3 simple steps:

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
    target_repo = "ddanieltan/my-dataset-repo"
    target_branch = "main"
    target_path = "data.json"
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
Add `.github/workflows/scrape-my-dataset.yml` with your desired cron frequency and target repository checkout.
