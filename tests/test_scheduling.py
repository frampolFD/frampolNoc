from app.monitoring.scheduling import effective_interval


def test_uses_global_default_when_no_override():
    assert effective_interval(None, 30) == 30


def test_uses_per_link_override_when_set():
    assert effective_interval(15, 30) == 15


def test_ignores_zero_or_negative_override():
    assert effective_interval(0, 30) == 30
    assert effective_interval(-5, 30) == 30
