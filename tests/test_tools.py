"""Tests for Gerty tools (alarms, timers, weather)."""

import json
import tempfile
from pathlib import Path

import pytest

from gerty.tools.alarms import AlarmsTool, _parse_alarm_time
from gerty.tools.number_words import normalize_time_words
from gerty.tools.weather import _extract_city


class TestNumberWords:
    def test_normalize_time(self):
        assert normalize_time_words("eleven oh five") == "11 5"
        assert normalize_time_words("seven thirty") == "7 30"
        assert normalize_time_words("seven thirty am") == "7 30 am"
        assert normalize_time_words("twenty five minutes") == "25 minutes"


class TestAlarmTimeParsing:
    def test_word_times(self):
        """Alarm times from STT: 'eleven oh five', 'seven thirty am'."""
        t = _parse_alarm_time("set alarm for eleven oh five")
        assert t is not None
        assert t.hour == 11
        assert t.minute == 5

        t = _parse_alarm_time("alarm for seven thirty am")
        assert t is not None
        assert t.hour == 7
        assert t.minute == 30


class TestWeatherExtraction:
    def test_forecast_for_city(self):
        assert _extract_city("what's the weather forecast for sheffield this afternoon") == "sheffield"
        assert _extract_city("forecast for sheffield") == "sheffield"

    def test_stt_ecast_fallback(self):
        """STT may drop 'weather for' -> 'ecast for sheffield'."""
        assert _extract_city("ecast for sheffield this afternoon") == "sheffield"

    def test_weather_for(self):
        assert _extract_city("weather for london") == "london"
