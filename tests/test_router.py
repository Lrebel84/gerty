"""Tests for LLM router intent classification and parsing."""

import pytest

from gerty.llm.router import classify_intent, parse_timer_duration


class TestClassifyIntent:
    def test_time(self):
        assert classify_intent("what time is it") == "time"
        assert classify_intent("current time") == "time"

    def test_date(self):
        assert classify_intent("what's the date") == "date"
        assert classify_intent("today's date") == "date"

    def test_timer_before_time(self):
        assert classify_intent("set a 5 minute timer") == "timer"
        assert classify_intent("timer for 10 minutes") == "timer"

    def test_alarm(self):
        assert classify_intent("set alarm for 7am") == "alarm"
        assert classify_intent("wake me at 6") == "alarm"

    def test_complex(self):
        assert classify_intent("explain quantum physics") == "complex"
        assert classify_intent("write code for a REST API") == "complex"

    def test_chat_default(self):
        assert classify_intent("hello") == "chat"
        assert classify_intent("tell me a joke") == "chat"

    def test_empty(self):
        assert classify_intent("") == "chat"
        assert classify_intent("   ") == "chat"


class TestParseTimerDuration:
    def test_minutes(self):
        assert parse_timer_duration("5 minutes") == 300
        assert parse_timer_duration("1 minute") == 60

    def test_hours(self):
        assert parse_timer_duration("2 hours") == 7200
        assert parse_timer_duration("1 hour") == 3600

    def test_seconds(self):
        assert parse_timer_duration("30 seconds") == 30

    def test_combined(self):
        assert parse_timer_duration("1 hour 30 minutes") == 5400

    def test_bare_number_assumes_minutes(self):
        assert parse_timer_duration("timer 5") == 300

    def test_none_for_invalid(self):
        assert parse_timer_duration("no numbers") is None
        assert parse_timer_duration("") is None
