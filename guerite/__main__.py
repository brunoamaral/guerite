from logging import getLogger
from time import sleep

from docker import DockerClient
from docker.errors import DockerException

from .config import Settings, load_settings
from .monitor import run_once
from .utils import configure_logging

LOG = getLogger(__name__)


def build_client(settings: Settings) -> DockerClient:
    try:
        return DockerClient(base_url=settings.docker_host)
    except DockerException as error:
        raise SystemExit(f"Unable to connect to Docker: {error}") from error


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    client = build_client(settings)
    LOG.info("Starting Guerite")
    while True:
        run_once(client, settings)
        sleep(settings.poll_interval)


if __name__ == "__main__":
    main()
