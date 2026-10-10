from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import requests

DEFAULT_LOCATION = "Thanjavur"
DEFAULT_LAT = 10.7867
DEFAULT_LON = 79.1378


def geocode_location(location: str) -> dict[str, Any]:
    query = (location or DEFAULT_LOCATION).strip()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(query)}&count=1&language=en&format=json"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("results"):
            raise ValueError("No geocoding result found")
        result = payload["results"][0]
        return {
            "location": query,
            "latitude": result.get("latitude", DEFAULT_LAT),
            "longitude": result.get("longitude", DEFAULT_LON),
            "country": result.get("country", "India"),
        }
    except Exception:
        return {
            "location": query,
            "latitude": DEFAULT_LAT,
            "longitude": DEFAULT_LON,
            "country": "India",
        }


def fetch_forecast(location: str) -> dict[str, Any]:
    geo = geocode_location(location)
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={geo['latitude']}&longitude={geo['longitude']}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum&"
        "hourly=temperature_2m,precipitation_probability,weather_code&forecast_days=7&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        body = response.json()
        daily = body.get("daily", {})
        summary = []
        for i, day in enumerate(daily.get("time", [])[:5]):
            summary.append(
                {
                    "date": day,
                    "max_temp_c": daily.get("temperature_2m_max", [])[i],
                    "min_temp_c": daily.get("temperature_2m_min", [])[i],
                    "rain_probability_pct": daily.get("precipitation_probability_max", [])[i],
                    "total_precip_mm": daily.get("precipitation_sum", [])[i],
                    "weather_code": daily.get("weather_code", [])[i],
                }
            )
        return {
            "location": geo["location"],
            "country": geo["country"],
            "summary": summary,
            "alert_level": "moderate" if summary and summary[0].get("rain_probability_pct", 0) > 60 else "low",
            "api_source": "Open-Meteo",
        }
    except Exception:
        fallback = [
            {"date": "Today", "max_temp_c": 34, "min_temp_c": 27, "rain_probability_pct": 68, "total_precip_mm": 12, "weather_code": 61},
            {"date": "Tomorrow", "max_temp_c": 35, "min_temp_c": 28, "rain_probability_pct": 55, "total_precip_mm": 8, "weather_code": 63},
            {"date": "Day 3", "max_temp_c": 33, "min_temp_c": 26, "rain_probability_pct": 50, "total_precip_mm": 9, "weather_code": 80},
        ]
        return {
            "location": geo["location"],
            "country": geo["country"],
            "summary": fallback,
            "alert_level": "moderate",
            "api_source": "mock fallback",
        }


def weather_code_to_label(code: int | None) -> str:
    mapping = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "heavy drizzle",
        61: "light rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "light snow",
        73: "moderate snow",
        75: "heavy snow",
        80: "rain showers",
        81: "heavy showers",
        82: "violent showers",
        95: "thunderstorm",
    }
    return mapping.get(code, "weather alert")


def build_weather_summary(forecast: dict[str, Any]) -> str:
    items = []
    for day in forecast["summary"][:3]:
        items.append(
            f"{day['date']}: {day['max_temp_c']}C max, {day['rain_probability_pct']}% rain chance, {weather_code_to_label(day.get('weather_code'))}"
        )
    return "; ".join(items)
