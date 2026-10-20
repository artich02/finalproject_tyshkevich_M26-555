from __future__ import annotations

import threading

from valutatrade_hub.parser_service.updater import RatesUpdater


class BackgroundScheduler:
    """Потоковый таймер"""

    def __init__(self, interval_seconds: int = 300) -> None:
        self.interval = interval_seconds
        self.updater = RatesUpdater()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.updater.run_update()
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def start(self) -> None:
        """запуск фонового потока обновления"""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """остановка фонового потока"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)