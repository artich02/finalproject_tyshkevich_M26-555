import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> logging.Logger:
    settings = SettingsLoader()
    log_file: Path = settings.get("LOG_FILE")
    log_level_name: str = settings.get("LOG_LEVEL", "INFO")
    max_bytes: int = settings.get("LOG_MAX_BYTES", 1048576)
    backup_count: int = settings.get("LOG_BACKUP_COUNT", 3)

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade")
    level = getattr(logging, log_level_name.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            fmt="%(levelname)s %(asctime)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger