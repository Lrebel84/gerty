"""Tests for LLM router intent classification and parsing."""

import pytest

from gerty.llm.router import classify_intent, parse_timer_duration
from gerty.tools.number_words import normalize_time_words


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

    def test_rag(self):
        assert classify_intent("check documentation") == "rag"
        assert classify_intent("retrieve the setup guide") == "rag"
        assert classify_intent("search my docs for API") == "rag"
        assert classify_intent("search my files for config") == "rag"
        assert classify_intent("what do my files say about X") == "rag"
        assert classify_intent("check my files for the report") == "rag"

    def test_chat_default(self):
        assert classify_intent("hello") == "chat"
        assert classify_intent("tell me a joke") == "chat"

    def test_calculator_genuine_math(self):
        assert classify_intent("what is 15% of 80") == "calculator"
        assert classify_intent("calculate 2 + 2") == "calculator"
        assert classify_intent("what's 10 times 5") == "calculator"
        assert classify_intent("2 + 2") == "calculator"

    def test_calculator_not_conversational_questions(self):
        """Questions starting with 'what's' or 'what is' but with no math go to chat."""
        assert classify_intent("what's the most controversial episode of South Park?") == "chat"
        assert classify_intent("What's better, the book or the film?") == "chat"
        assert classify_intent("what is the capital of France") == "chat"

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

    def test_number_words_stt(self):
        """STT may say 'five minutes' instead of '5 minutes'."""
        assert parse_timer_duration(normalize_time_words("five minutes")) == 300
        assert parse_timer_duration(normalize_time_words("twenty minutes")) == 1200
        assert parse_timer_duration(normalize_time_words("timer for ten minutes")) == 600

    def test_none_for_invalid(self):
        assert parse_timer_duration("no numbers") is None
        assert parse_timer_duration("") is None
