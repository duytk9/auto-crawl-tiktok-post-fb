from datetime import UTC, date, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utc_today() -> date:
    return utc_now().date()
