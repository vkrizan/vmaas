"""
Wait for VMaaS services.
"""
import os
import signal
import sys
import time

from psycopg2 import OperationalError
from requests import request

from vmaas.common.config import Config
from vmaas.common.logging_utils import get_logger, init_logging
from vmaas.reposcan.database.database_handler import DatabaseHandler, init_db

LOGGER = get_logger(__file__)


def bye(signum, _):
    """Handle signal"""
    sys.exit(f"Stopped,{signum} received.")


def wait(func, *args, delay=1, service="", **kwargs):
    """Waits for success of `func`."""
    LOGGER.info("Checking if %s is up", service)
    while True:
        try:
            result = func(*args, **kwargs)
            if result:
                return
            LOGGER.info("%s is unavailable - sleeping", service)
            time.sleep(delay)
        except OperationalError as err:
            LOGGER.info(
                "%s is unavailable, pgerror: %s, pgcode: %s - sleeping",
                service,
                err.pgerror,
                err.pgcode
            )
            time.sleep(delay)
        except:  # noqa pylint: disable=bare-except
            LOGGER.info("%s is unavailable - sleeping", service)
            time.sleep(delay)


def main():
    """Wait for services."""
    init_logging()
    init_db()
    config = Config()
    if config.db_available:
        wait(DatabaseHandler.get_connection, service="PostgreSQL")
    else:
        LOGGER.info("Skipping PostgreSQL check")
    if config.websocket_host and "vmaas-websocket" not in config.pod_hostname and not config.is_init_container:
        wait(
            request,
            "GET",
            f"http://{config.websocket_host}:{config.websocket_port}/api/v1/monitoring/health",
            service="Websocket server",
            timeout=1,
        )
    else:
        LOGGER.info("Skipping Websocket server check")
    if config.reposcan_host and "vmaas-reposcan" not in config.pod_hostname:
        wait(
            request,
            "GET",
            f"http://{config.reposcan_host}:{config.reposcan_port}/api/v1/monitoring/health",
            service="Reposcan API",
            timeout=1,
        )
    else:
        LOGGER.info("Skipping Reposcan API check")

    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)
    main()
