"""Tests for Gerty tools (alarms, timers, weather)."""

import json
import tempfile
from pathlib import Path

import pytest

from gerty.tools.alarms import AlarmsTool, _parse_alarm_time, _parse_alarm_label, _parse_recurring, add_alarm, get_pending_alarms, reschedule_daily_alarm, toggle_alarm_recurring
from gerty.tools.timers import add_timer, cancel_timer, get_active_timers, cancel_all_timers
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

    def test_dot_separator_pm(self):
        """Alarm times with dot: '6.32pm' (STT may use dot instead of colon)."""
        t = _parse_alarm_time("set an alarm for 6.32pm")
        assert t is not None
        assert t.hour == 18
        assert t.minute == 32

    def test_space_separator_pm(self):
        """Alarm times with space and pm: '6 32 pm'."""
        t = _parse_alarm_time("alarm for 6 32 pm")
        assert t is not None
        assert t.hour == 18
        assert t.minute == 32


class TestAddAlarm:
    def test_add_alarm_api(self, monkeypatch, tmp_path):
        """add_alarm creates alarm in file, get_pending_alarms returns it."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        alarm = add_alarm("7:30 am", "Wake")
        assert "id" in alarm
        assert alarm["label"] == "Wake"
        assert "07:30" in alarm["time"] or "7:30" in alarm["time"]
        pending = get_pending_alarms()
        assert len(pending) >= 1
        assert any(a.get("label") == "Wake" for a in pending)

    def test_add_alarm_invalid_time(self, monkeypatch, tmp_path):
        """add_alarm raises ValueError for unparseable time."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        with pytest.raises(ValueError, match="Could not parse"):
            add_alarm("not a time", "Test")

    def test_pending_alarms_includes_sounding(self, monkeypatch, tmp_path):
        """Triggered alarm stays in list until cancelled (include_sounding_id)."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        from datetime import datetime, timedelta
        alarm = add_alarm("7:00 am", "Wake")
        aid = alarm["id"]
        # Simulate alarm that has triggered (past) - manually add to file with past time
        import json
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        with open(tmp_path / "alarms.json") as f:
            data = json.load(f)
        for a in data:
            if a["id"] == aid:
                a["datetime"] = past
                break
        with open(tmp_path / "alarms.json", "w") as f:
            json.dump(data, f, indent=2)
        # Without include_sounding_id, triggered alarm is filtered out
        pending = get_pending_alarms()
        assert len(pending) == 0
        # With include_sounding_id, triggered alarm stays in list
        pending_with_sounding = get_pending_alarms(include_sounding_id=aid)
        assert len(pending_with_sounding) == 1
        assert pending_with_sounding[0]["sounding"] is True
        assert pending_with_sounding[0]["id"] == aid


class TestAlarmLabel:
    def test_parse_alarm_label(self):
        """Voice: 'alarm for 7am for workout' -> label 'workout'."""
        assert _parse_alarm_label("set alarm for 7am for workout") == "workout"
        assert _parse_alarm_label("alarm for 7:30 for eggs") == "eggs"
        assert _parse_alarm_label("alarm for 7am") == "Alarm"


class TestAlarmRecurring:
    def test_parse_recurring(self):
        """Voice: 'daily' or 'repeat' -> recurring."""
        assert _parse_recurring("daily alarm for 7am") == "daily"
        assert _parse_recurring("alarm for 7am every day") == "daily"
        assert _parse_recurring("repeating alarm at 6pm") == "daily"
        assert _parse_recurring("alarm for 7am") is None

    def test_add_daily_alarm(self, monkeypatch, tmp_path):
        """add_alarm with recurring='daily' creates daily alarm."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        alarm = add_alarm("7:30 am", "Wake", recurring="daily")
        assert alarm.get("recurring") == "daily"
        pending = get_pending_alarms()
        assert any(a.get("recurring") == "daily" for a in pending)

    def test_reschedule_daily_alarm(self, monkeypatch, tmp_path):
        """reschedule_daily_alarm moves alarm to tomorrow."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        from datetime import datetime, timedelta
        alarm = add_alarm("7:00 am", recurring="daily")
        aid = alarm["id"]
        # Simulate triggered: set datetime to past
        import json
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        with open(tmp_path / "alarms.json") as f:
            data = json.load(f)
        for a in data:
            if a["id"] == aid:
                a["datetime"] = past
                break
        with open(tmp_path / "alarms.json", "w") as f:
            json.dump(data, f, indent=2)
        ok = reschedule_daily_alarm(aid)
        assert ok
        with open(tmp_path / "alarms.json") as f:
            data = json.load(f)
        for a in data:
            if a["id"] == aid:
                dt = datetime.fromisoformat(a["datetime"])
                assert dt > datetime.now()
                break

    def test_toggle_alarm_recurring(self, monkeypatch, tmp_path):
        """toggle_alarm_recurring switches between daily and one-time."""
        monkeypatch.setattr("gerty.tools.alarms.ALARMS_FILE", tmp_path / "alarms.json")
        monkeypatch.setattr("gerty.tools.alarms.DATA_DIR", tmp_path)
        alarm = add_alarm("7:00 am")
        aid = alarm["id"]
        assert toggle_alarm_recurring(aid) == "daily"
        pending = get_pending_alarms()
        assert any(a.get("recurring") == "daily" for a in pending)
        assert toggle_alarm_recurring(aid) is None
        pending = get_pending_alarms()
        assert not any(a.get("recurring") == "daily" for a in pending)


class TestAddTimer:
    def test_add_timer_api(self):
        """add_timer creates timer, get_active_timers returns it, cancel_timer removes it."""
        cancel_all_timers()
        result = add_timer(60, "Test")
        assert "id" in result
        assert result["label"] == "Test"
        assert result["duration_sec"] == 60
        timers = get_active_timers()
        assert len(timers) == 1
        assert timers[0]["label"] == "Test"
        assert timers[0]["remaining_sec"] <= 60
        ok = cancel_timer(result["id"])
        assert ok
        assert len(get_active_timers()) == 0

    def test_add_timer_invalid_duration(self):
        """add_timer raises ValueError for non-positive duration."""
        with pytest.raises(ValueError, match="positive"):
            add_timer(0, "Test")
        with pytest.raises(ValueError, match="positive"):
            add_timer(-5, "Test")


class TestWeatherExtraction:
    def test_forecast_for_city(self):
        assert _extract_city("what's the weather forecast for sheffield this afternoon") == "sheffield"
        assert _extract_city("forecast for sheffield") == "sheffield"

    def test_stt_ecast_fallback(self):
        """STT may drop 'weather for' -> 'ecast for sheffield'."""
        assert _extract_city("ecast for sheffield this afternoon") == "sheffield"

    def test_weather_for(self):
        assert _extract_city("weather for london") == "london"
