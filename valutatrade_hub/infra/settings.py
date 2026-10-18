from __future__ import annotations

from pathlib import Path
from typing import Any


class SettingsLoader:

    _instance: SettingsLoader | None = None
    _initialized: bool = False

    def __new__(cls) -> SettingsLoader:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        base_dir = Path(__file__).resolve().parent.parent.parent
        self._settings: dict[str, Any] = {
            "BASE_DIR": base_dir,
            "DATA_DIR": base_dir / "data",
            "LOGS_DIR": base_dir / "logs",
            "USERS_FILE": base_dir / "data" / "users.json",
            "PORTFOLIOS_FILE": base_dir / "data" / "portfolios.json",
            "RATES_FILE": base_dir / "data" / "rates.json",
            "LOG_FILE": base_dir / "logs" / "actions.log",
            "DEFAULT_BASE_CURRENCY": "USD",
            "RATES_TTL_SECONDS": 300,
            "LOG_LEVEL": "INFO",
            "LOG_MAX_BYTES": 1_048_576,  # 1 MB
            "LOG_BACKUP_COUNT": 3,
        }
        self._ensure_dirs()
        self._initialized = True

    def _ensure_dirs(self) -> None:
        """создание директорий"""
        self._settings["DATA_DIR"].mkdir(parents=True, exist_ok=True)
        self._settings["LOGS_DIR"].mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Получение параметра конфигурации по ключу"""
        return self._settings.get(key, default)

    def reload(self) -> None:
        """Сброс и повторная инициализация настроек"""
        self._initialized = False
        self.__init__()