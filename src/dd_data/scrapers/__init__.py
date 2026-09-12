"""Scraper implementations for dd-data."""

from dd_data.scrapers.daily_weather import DailyWeatherScraper
from dd_data.scrapers.hourly_rainfall import HourlyRainfallScraper

__all__ = ["DailyWeatherScraper", "HourlyRainfallScraper"]
