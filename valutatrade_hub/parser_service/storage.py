from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


class RatesStorage:
    """менеджер атомарного сохранения истории и среза курсов"""

    def __init__(self, rates_file: Path, history_file: Path) -> None:
        self.rates_file = rates_file
        self.history_file = history_file
        self._ensure_files()

    def _ensure_files(self) -> None:
        self.rates_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._atomic_write(self.history_file, [])
        if not self.rates_file.exists():
            self._atomic_write(self.rates_file, {"pairs": {}, "last_refresh": ""})

    @staticmethod
    def _atomic_write(target_path: Path, data: Any) -> None:
        """атомарная запись через временный файл в той же директории"""
        dir_name = target_path.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=dir_name,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(json.dumps(data, indent=2, ensure_ascii=False))
            tmp_name = tmp.name

        Path(tmp_name).replace(target_path)

    def load_history(self) -> list[dict[str, Any]]:
        try:
            content = self.history_file.read_text(encoding="utf-8")
            raw = json.loads(content)
            return raw if isinstance(raw, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def append_history(self, records: list[dict[str, Any]]) -> None:
        history = self.load_history()
        existing_ids = {item["id"] for item in history if "id" in item}

        for r in records:
            if r["id"] not in existing_ids:
                history.append(r)
                existing_ids.add(r["id"])

        self._atomic_write(self.history_file, history)

    def load_rates_snapshot(self) -> dict[str, Any]:
        """чтение текущего среза курсов rates.json"""
        try:
            content = self.rates_file.read_text(encoding="utf-8")
            raw = json.loads(content)
            return raw if isinstance(raw, dict) else {"pairs": {}, "last_refresh": ""}
        except (json.JSONDecodeError, OSError):
            return {"pairs": {}, "last_refresh": ""}

    def save_rates_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._atomic_write(self.rates_file, snapshot)