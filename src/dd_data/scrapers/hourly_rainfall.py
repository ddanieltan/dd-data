"""Hourly Rainfall scraper for ddanieltan/sg-hourly-rainfall."""

from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field, model_validator

from dd_data.core.base import BaseScraper, registry


class StationLocation(BaseModel):
    latitude: float
    longitude: float


class RainfallStation(BaseModel):
    id: str
    deviceId: Optional[str] = None
    name: str
    location: StationLocation


class RainfallReadingItem(BaseModel):
    stationId: str
    value: float


class RainfallReadingBlock(BaseModel):
    timestamp: str
    data: List[RainfallReadingItem] = Field(default_factory=list)


class RainfallData(BaseModel):
    stations: List[RainfallStation] = Field(..., min_length=1)
    readings: List[RainfallReadingBlock] = Field(..., min_length=1)
    readingType: Optional[str] = None
    readingUnit: Optional[str] = None


class HourlyRainfallPayload(BaseModel):
    """Schema guard for real-time rainfall payload from api-open.data.gov.sg."""

    code: int
    data: RainfallData
    errorMsg: Optional[str] = None

    @model_validator(mode="after")
    def check_response_code(self) -> "HourlyRainfallPayload":
        if self.code != 0:
            raise ValueError(f"Upstream returned non-zero code {self.code}: {self.errorMsg}")
        return self


@registry.register
class HourlyRainfallScraper(BaseScraper):
    name = "hourly-rainfall"
    description = "Hourly rainfall readings from Singapore api-open.data.gov.sg"
    target_repo = "ddanieltan/sg-hourly-rainfall"
    target_branch = "main"
    target_path = "api-open.data.gov.sg-v2-real-time-api-rainfall.json"
    schema = HourlyRainfallPayload

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch(self) -> Any:
        url = "https://api-open.data.gov.sg/v2/real-time/api/rainfall"

        headers = {
            "Accept": "application/json",
            "User-Agent": "dd-data-scraper/1.0",
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data
