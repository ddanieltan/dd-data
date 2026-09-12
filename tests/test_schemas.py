"""Unit tests for schema guards, validation, and registry."""

import pytest
from pydantic import ValidationError

from dd_data.core.base import registry
from dd_data.scrapers.daily_weather import DailyWeatherPayload, DailyWeatherScraper
from dd_data.scrapers.hourly_rainfall import HourlyRainfallPayload, HourlyRainfallScraper


def test_registry_registration() -> None:
    """Test that all scrapers are registered with expected names."""
    all_scrapers = registry.all()
    assert "daily-weather" in all_scrapers
    assert "hourly-rainfall" in all_scrapers

    scraper = registry.get("daily-weather")
    assert isinstance(scraper, DailyWeatherScraper)
    assert scraper.target_repo == "ddanieltan/daily-weather-sg"

    with pytest.raises(KeyError):
        registry.get("non-existent-scraper")


def test_daily_weather_schema_valid() -> None:
    """Test daily weather schema with realistic valid payload."""
    payload = {
        "metadata": {
            "stations": [
                {
                    "id": "S109",
                    "device_id": "S109",
                    "name": "Ang Mo Kio",
                    "location": {"latitude": 1.3793, "longitude": 103.85},
                }
            ],
            "reading_type": "DBT 1M F",
            "reading_unit": "deg C",
        },
        "items": [
            {
                "timestamp": "2026-09-12T12:00:00+08:00",
                "readings": [{"station_id": "S109", "value": 31.4}],
            }
        ],
        "api_info": {"status": "healthy"},
    }

    validated = DailyWeatherPayload.model_validate(payload)
    assert len(validated.items) == 1
    assert validated.items[0].readings[0].value == 31.4


def test_daily_weather_schema_empty_items_rejected() -> None:
    """Test that empty items list fails validation."""
    payload = {
        "metadata": {
            "stations": [
                {
                    "id": "S109",
                    "name": "Ang Mo Kio",
                    "location": {"latitude": 1.3793, "longitude": 103.85},
                }
            ]
        },
        "items": [],
    }

    with pytest.raises(ValidationError):
        DailyWeatherPayload.model_validate(payload)


def test_daily_weather_schema_corrupt_payload_rejected() -> None:
    """Test that upstream error responses (e.g. HTML or generic 500 json) fail validation."""
    corrupt_payload = {
        "code": 500,
        "message": "Internal server error occurred while retrieving stations",
    }

    with pytest.raises(ValidationError):
        DailyWeatherPayload.model_validate(corrupt_payload)


def test_hourly_rainfall_schema_valid() -> None:
    """Test hourly rainfall schema with realistic valid payload."""
    payload = {
        "code": 0,
        "data": {
            "stations": [
                {
                    "id": "S218",
                    "deviceId": "S218",
                    "name": "Bukit Batok",
                    "location": {"latitude": 1.36491, "longitude": 103.75065},
                }
            ],
            "readings": [
                {
                    "timestamp": "2026-09-12T12:00:00+08:00",
                    "data": [{"stationId": "S218", "value": 0.0}],
                }
            ],
            "readingType": "rainfall",
            "readingUnit": "mm",
        },
        "errorMsg": None,
    }

    validated = HourlyRainfallPayload.model_validate(payload)
    assert validated.code == 0
    assert len(validated.data.stations) == 1
    assert validated.data.readings[0].data[0].value == 0.0


def test_hourly_rainfall_schema_nonzero_code_rejected() -> None:
    """Test that non-zero response code fails validation."""
    payload = {
        "code": 1002,
        "data": {
            "stations": [
                {
                    "id": "S218",
                    "name": "Bukit Batok",
                    "location": {"latitude": 1.36491, "longitude": 103.75065},
                }
            ],
            "readings": [
                {
                    "timestamp": "2026-09-12T12:00:00+08:00",
                    "data": [{"stationId": "S218", "value": 0.0}],
                }
            ],
        },
        "errorMsg": "Rate limit exceeded",
    }

    with pytest.raises(ValidationError, match="Upstream returned non-zero code"):
        HourlyRainfallPayload.model_validate(payload)


def test_payload_formatting_deterministic() -> None:
    """Test that scraper format_payload sorts keys and adds trailing newline."""
    scraper = DailyWeatherScraper()
    payload = {
        "metadata": {
            "stations": [
                {
                    "name": "Ang Mo Kio",
                    "id": "S109",
                    "location": {"longitude": 103.85, "latitude": 1.3793},
                }
            ]
        },
        "items": [
            {
                "timestamp": "2026-09-12T12:00:00+08:00",
                "readings": [{"value": 29.5, "station_id": "S109"}],
            }
        ],
    }

    validated = scraper.validate_payload(payload)
    formatted = scraper.format_payload(validated)

    assert formatted.endswith("\n")
    # Verify deterministic key order (e.g. "api_info" or "items" before "metadata")
    assert formatted.index('"items"') < formatted.index('"metadata"')
