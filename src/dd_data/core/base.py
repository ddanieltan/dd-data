"""Base scraper definition and registry."""

from abc import ABC, abstractmethod
import json
from typing import Any, ClassVar, Dict, Type
from pydantic import BaseModel, ValidationError

from dd_data.core.logger import log_error, log_info, log_success


class ScraperRegistry:
    """Registry holding all registered scrapers."""

    def __init__(self) -> None:
        self._scrapers: Dict[str, BaseScraper] = {}

    def register(self, scraper_cls: Type["BaseScraper"]) -> Type["BaseScraper"]:
        instance = scraper_cls()
        if instance.name in self._scrapers:
            raise ValueError(f"Scraper with name '{instance.name}' already registered.")
        self._scrapers[instance.name] = instance
        return scraper_cls

    def get(self, name: str) -> "BaseScraper":
        if name not in self._scrapers:
            available = ", ".join(self._scrapers.keys())
            raise KeyError(f"Scraper '{name}' not found. Available scrapers: {available}")
        return self._scrapers[name]

    def all(self) -> Dict[str, "BaseScraper"]:
        return dict(self._scrapers)


registry = ScraperRegistry()


class BaseScraper(ABC):
    """Abstract Base Class for all Git-Scrapers."""

    name: ClassVar[str]
    description: ClassVar[str]
    target_repo: ClassVar[str]
    target_branch: ClassVar[str] = "main"
    target_path: ClassVar[str]
    schema: ClassVar[Type[BaseModel]]

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch raw data from upstream API.

        Raises:
            httpx.HTTPError: If network or HTTP status check fails.
        """
        pass

    def validate_payload(self, raw_data: Any) -> BaseModel:
        """Validate raw payload against the Pydantic schema model.

        Raises:
            ValidationError: If schema is not satisfied, payload is empty, or malformed.
        """
        if not raw_data:
            raise ValueError(f"[{self.name}] Empty payload received from upstream API.")

        try:
            validated = self.schema.model_validate(raw_data)
            return validated
        except ValidationError as e:
            log_error(f"[{self.name}] Schema validation failed: {e}")
            raise

    def format_payload(self, validated: BaseModel) -> str:
        """Serialize validated data into deterministic, clean JSON for minimal git diffs.

        Uses 2-space indentation, sorted keys, and guarantees a trailing newline.
        """
        # Convert model to python dict, then serialize with sort_keys=True
        data_dict = validated.model_dump(mode="json")
        formatted = json.dumps(data_dict, indent=2, sort_keys=True, ensure_ascii=False)
        return formatted + "\n"

    def execute(self) -> str:
        """Runs the complete scrape and validation cycle, returning the formatted string."""
        log_info(f"[{self.name}] Fetching upstream data...")
        raw_data = self.fetch()

        log_info(f"[{self.name}] Validating payload against schema...")
        validated = self.validate_payload(raw_data)

        log_success(f"[{self.name}] Schema validation succeeded.")
        return self.format_payload(validated)
