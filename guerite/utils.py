from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from logging import basicConfig, getLogger

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LOG = getLogger(__name__)


def configure_logging(level: str) -> None:
    basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, level=level)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_tz(tz_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception as error:
        LOG.warning("Falling back to UTC; invalid timezone %s: %s", tz_name, error)
        return datetime.now(timezone.utc)
