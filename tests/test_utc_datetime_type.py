from datetime import datetime, timezone

from app.database import UTCDateTime


def test_naive_result_gets_utc_tzinfo_attached():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = UTCDateTime().process_result_value(naive, dialect=None)
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_aware_result_passes_through_unchanged():
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert UTCDateTime().process_result_value(aware, dialect=None) is aware


def test_none_passes_through():
    assert UTCDateTime().process_result_value(None, dialect=None) is None
