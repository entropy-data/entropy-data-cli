"""Tests for time ranges and paging of list commands (usage, lineage, test results)."""

from datetime import datetime, timezone

import pytest
import typer

from entropy_data.listing import TimeRange, parse_time, parse_unix_nanos, to_param

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("30m", datetime(2026, 10, 9, 11, 30, tzinfo=timezone.utc)),
        ("24h", datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)),
        ("7d", datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)),
        ("2w", datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)),
        ("2026-10-01", datetime(2026, 10, 1, tzinfo=timezone.utc)),
        ("2026-10-01T08:15:00", datetime(2026, 10, 1, 8, 15, tzinfo=timezone.utc)),
        ("2026-10-01T08:15:00Z", datetime(2026, 10, 1, 8, 15, tzinfo=timezone.utc)),
        ("2026-10-01T10:15:00+02:00", datetime(2026, 10, 1, 8, 15, tzinfo=timezone.utc)),
    ],
)
def test_parse_time(value, expected):
    assert parse_time(value, NOW) == expected


@pytest.mark.parametrize("value", ["yesterday", "7x", "2026-13-01", ""])
def test_parse_time_rejects(value):
    with pytest.raises(typer.BadParameter):
        parse_time(value, NOW)


def test_to_param_is_utc():
    assert to_param(datetime.fromisoformat("2026-10-01T10:15:00+02:00")) == "2026-10-01T08:15:00Z"


def test_time_range_since_must_precede_until():
    with pytest.raises(typer.BadParameter):
        TimeRange.parse("2026-10-02", "2026-10-01")


def test_time_range_contains_is_inclusive_exclusive():
    time_range = TimeRange.parse("2026-10-01", "2026-10-02")
    assert time_range.contains(datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert not time_range.contains(datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert not time_range.contains(None)
    assert TimeRange().contains(None)


def test_parse_unix_nanos_takes_strings_and_numbers():
    assert parse_unix_nanos("1759996800000000000") == datetime(2025, 10, 9, 8, 0, tzinfo=timezone.utc)
    assert parse_unix_nanos(1759996800000000000) == datetime(2025, 10, 9, 8, 0, tzinfo=timezone.utc)
    assert parse_unix_nanos(None) is None
