from datetime import datetime, timedelta, timezone

import pytest

from app.monitoring.worker import _aware_utc


def test_naive_datetime_gets_utc_attached():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = _aware_utc(naive)
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_aware_datetime_passes_through_unchanged():
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert _aware_utc(aware) is aware


def test_none_passes_through():
    assert _aware_utc(None) is None


def test_subtraction_against_fresh_now_does_not_raise():
    # This is the exact failure mode the SQLite round-trip caused: a
    # naive datetime loaded from the DB subtracted from a fresh
    # timezone-aware datetime.now(timezone.utc) raises TypeError unless
    # the loaded value is coerced first.
    now = datetime.now(timezone.utc)
    loaded_from_db = (now - timedelta(seconds=45)).replace(tzinfo=None)
    elapsed = (now - _aware_utc(loaded_from_db)).total_seconds()
    assert elapsed == pytest.approx(45, abs=1)
