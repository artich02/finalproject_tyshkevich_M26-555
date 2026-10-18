from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.core.constants import DEFAULT_PAIR_RATES
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:

    _instance: DatabaseManager | None = None
    _initialized: bool = False

    def __new__(cls) -> DatabaseManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        settings = SettingsLoader()
        self.users_file: Path = settings.get("USERS_FILE")
        self.portfolios_file: Path = settings.get("PORTFOLIOS_FILE")
        self.rates_file: Path = settings.get("RATES_FILE")
        self._ensure_files()
        self._initialized = True

    def _ensure_files(self) -> None:
        """Инициализация файлов при их отсутствии"""
        for f in (self.users_file, self.portfolios_file):
            if not f.exists():
                f.write_text("[]", encoding="utf-8")

        if not self.rates_file.exists() or self.rates_file.stat().st_size == 0:
            now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            initial = {
                pair: {"rate": r, "updated_at": now_iso}
                for pair, r in DEFAULT_PAIR_RATES.items()
            }
            initial["source"] = "ParserService"
            initial["last_refresh"] = now_iso
            self.rates_file.write_text(
                json.dumps(initial, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def read_json(self, file_path: Path) -> Any:
        """безопасно чтение данных"""
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return [] if file_path != self.rates_file else {}

    def write_json(self, file_path: Path, data: Any) -> None:
        """безопасная запись данных"""
        file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )