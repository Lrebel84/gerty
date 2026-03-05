"""Weather tool: current conditions via Open-Meteo (no API key)."""

import logging

import httpx

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0

# WMO weather codes -> short description
WEATHER_CODES = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    61: "rain",
    63: "rain",
    65: "heavy rain",
    71: "snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _geocode(city: str) -> tuple[float, float, str] | None:
    """Return (lat, lon, timezone) or None."""
    try:
        r = httpx.get(
            GEOCODING_URL,
            params={"name": city, "count": 1},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None
        loc = results[0]
        return (
            loc["latitude"],
            loc["longitude"],
            loc.get("timezone", "UTC"),
        )
    except Exception as e:
        logger.debug("Geocoding failed: %s", e)
        return None


def _fetch_weather(lat: float, lon: float, tz: str) -> dict | None:
    """Fetch current weather. Returns dict or None."""
    try:
        r = httpx.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": tz,
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        logger.debug("Weather fetch failed: %s", e)
        return None


def _extract_city(message: str) -> str | None:
    """Extract city/location from message."""
    lower = message.lower()
    for phrase in ["weather in", "weather at", "weather for", "forecast for"]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            return message[idx:].strip().rstrip("?.,") or None
    if "weather" in lower or "forecast" in lower:
        # "what's the weather" - use a default or try to extract
        words = message.split()
        for i, w in enumerate(words):
            if w.lower() in ("in", "at", "for") and i + 1 < len(words):
                return " ".join(words[i + 1 :]).strip().rstrip("?.,")
        # Default to empty - we'll use a fallback
        return None
    return None


class WeatherTool(Tool):
    """Current weather via Open-Meteo."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Current weather for a city"

    def execute(self, intent: str, message: str) -> str:
        city = _extract_city(message)
        if not city or len(city) < 2:
            return "Try: weather in London, or forecast for Tokyo"
        geo = _geocode(city)
        if not geo:
            return f"I couldn't find a location for '{city}'. Try a well-known city name."
        lat, lon, tz = geo
        data = _fetch_weather(lat, lon, tz)
        if not data:
            return "Could not fetch weather. Please try again later."
        curr = data.get("current", {})
        temp = curr.get("temperature_2m")
        code = curr.get("weather_code", 0)
        humidity = curr.get("relative_humidity_2m")
        wind = curr.get("wind_speed_10m")
        desc = WEATHER_CODES.get(code, "unknown")
        parts = [f"**{city.title()}**: {desc}, **{temp}°C**"]
        if humidity is not None:
            parts.append(f"{humidity}% humidity")
        if wind is not None:
            parts.append(f"{wind} km/h wind")
        return ". ".join(parts) + "."
