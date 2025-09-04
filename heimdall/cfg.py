"""Config module"""

from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from decouple import config as get_env

# General options

BASE_DIR: Path = Path(__file__).parent
DEBUG: bool = cast(bool, get_env("HD_DEBUG", cast=bool, default=True))
TZ: ZoneInfo = cast(ZoneInfo, get_env("HD_TZ", default="Europe/Oslo"))
CONFIG_FILE = Path("config.json")

# Email settings
EMAIL_ADDRESS = "Heimdall <system@ulv.io>"
EMAIL_RECIPIENT = get_env("HD_EMAIL_RECIPIENT")
EMAIL_SMTP_SERVER = "smtp-relay.gmail.com"
EMAIL_SMTP_PORT = 587

# Uvicorn settings
HOST: str = cast(str, get_env("HD_HOST", default="0.0.0.0"))
PORT: int = cast(int, get_env("HD_PORT", default=8000))
FORWARDED_ALLOWED_IPS: list[str] = cast(str, get_env("HD_FORWARDED_ALLOWED_IPS", default="")).split(",")

# Database options

DB_FILE = get_env("HD_DB_FILE", default="db.sqlite3")
DB_URI = f"sqlite:///./{DB_FILE}"

# Polling options

# Poll interval in seconds
POLL_INTERVAL: int = cast(int, get_env("HD_POLL_INTERVAL", cast=int, default=60 * 10))
# Poll timeout in seconds
POLL_TIMEOUT: int = cast(int, get_env("HD_POLL_TIMEOUT", cast=int, default=10))
# Poll task staggering time (to prevent bursts)
POLL_STAGGER_TIME: float = cast(float, get_env("HD_POLL_STAGGER_TIME", cast=float, default=0.25))

# Logging options

LOG_LEVEL = cast(str, get_env("HD_LOG_LEVEL", default="DEBUG")).upper()
LOG_FMT: str = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s"
LOG_DATE_FMT: str = "%Y-%m-%d %H:%M:%S"
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FMT,
            "datefmt": LOG_DATE_FMT,
        },
        "uvicorn": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)s uvicorn: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "uvicorn.error": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "uvicorn",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "aiosqlite": {"level": "INFO"},
        "databases": {"level": "INFO"},
        "uvicorn.error": {
            "handlers": ["uvicorn.error"],
            "propagate": False,
        },
        "root": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
        },
    },
}
