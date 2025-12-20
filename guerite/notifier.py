from http.client import HTTPSConnection
from logging import getLogger
from typing import Optional
from urllib.parse import urlencode, urlsplit

from .config import Settings

LOG = getLogger(__name__)


def notify_pushover(settings: Settings, title: str, message: str) -> None:
    if settings.pushover_token is None or settings.pushover_user is None:
        LOG.debug("Pushover disabled; missing token or user")
        return

    endpoint = urlsplit(settings.pushover_api)
    connection = HTTPSConnection(endpoint.netloc)
    body = urlencode(
        {
            "token": settings.pushover_token,
            "user": settings.pushover_user,
            "title": title,
            "message": message,
        }
    ).encode("ascii")
    path = endpoint.path or "/"
    if endpoint.query:
        path = f"{path}?{endpoint.query}"

    try:
        connection.request(
            "POST", path, body=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response = connection.getresponse()
        if response.status >= 300:
            LOG.warning("Pushover returned %s: %s", response.status, response.reason)
    except OSError as error:
        LOG.warning("Failed to send Pushover notification: %s", error)
    finally:
        connection.close()
