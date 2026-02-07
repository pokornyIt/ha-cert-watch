from datetime import UTC

from custom_components.cert_watch.coordinator import _parse_not_after


def test_parse_not_after() -> None:
    dt = _parse_not_after("Jun  1 12:00:00 2026 GMT")
    assert dt.tzinfo is UTC
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 1
    assert dt.hour == 12
