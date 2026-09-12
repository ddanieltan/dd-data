"""Daily Weather (Air Temperature) scraper for ddanieltan/daily-weather-sg."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field, field_validator

from dd_data.core.base import BaseScraper, registry


class StationLocation(BaseModel):
    latitude: float
    longitude: float


class WeatherStation(BaseModel):
    id: str
    device_id: Optional[str] = None
    name: str
    location: StationLocation


class WeatherReading(BaseModel):
    station_id: str
    value: float


class WeatherItem(BaseModel):
    timestamp: str
    readings: List[WeatherReading] = Field(..., min_length=1)


class WeatherMetadata(BaseModel):
    stations: List[WeatherStation] = Field(..., min_length=1)
    reading_type: Optional[str] = None
    reading_unit: Optional[str] = None


class DailyWeatherPayload(BaseModel):
    """Schema guard for daily air temperature response."""

    metadata: WeatherMetadata
    items: List[WeatherItem] = Field(..., min_length=1)
    api_info: Optional[Dict[str, Any]] = None

    @field_validator("items")
    @classmethod
    def check_items_not_empty(cls, v: List[WeatherItem]) -> List[WeatherItem]:
        if not v:
            raise ValueError("Weather payload contains empty items list.")
        return v


@registry.register
class DailyWeatherScraper(BaseScraper):
    name = "daily-weather"
    description = "Daily air temperature readings from Singapore data.gov.sg"
    target_repo = "ddanieltan/daily-weather-sg"
    target_branch = "main"
    target_path = "weather.json"
    schema = DailyWeatherPayload

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch(self) -> Any:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"https://api.data.gov.sg/v1/environment/air-temperature?date={today}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "dd-data-scraper/1.0",
        }

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data
