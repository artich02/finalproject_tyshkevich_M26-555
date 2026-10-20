from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Сервис опроса API, формирования журнала и актуализации среза"""

    def __init__(
        self,
        config: ParserConfig | None = None,
        clients: list[tuple[str, BaseApiClient]] | None = None,
        storage: RatesStorage | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.storage = storage or RatesStorage(
            rates_file=self.config.RATES_FILE_PATH,
            history_file=self.config.HISTORY_FILE_PATH,
        )
        self.clients = clients or [
            ("CoinGecko", CoinGeckoClient(self.config)),
            ("ExchangeRate-API", ExchangeRateApiClient(self.config)),
        ]
        self.logger = logging.getLogger("valutatrade")

    def run_update(
        self,
        source_filter: str | None = None,
    ) -> tuple[int, str, list[str]]:
        self.logger.info("Starting rates update...")
        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        merged_pairs: dict[str, Any] = {}
        history_records: list[dict[str, Any]] = []
        errors: list[str] = []

        snapshot = self.storage.load_rates_snapshot()
        current_pairs = snapshot.get("pairs", {})

        for name, client in self.clients:
            if source_filter and source_filter.lower() not in name.lower():
                continue

            try:
                rates = client.fetch_rates()
                self.logger.info("Fetching from %s... OK (%d rates)", name, len(rates))

                for pair_key, payload in rates.items():
                    merged_pairs[pair_key] = {
                        "rate": payload["rate"],
                        "updated_at": now_utc,
                        "source": payload["source"],
                    }

                    record_id = (
                        f"{payload['from_currency']}_"
                        f"{payload['to_currency']}_{now_utc}"
                    )
                    history_records.append({
                        "id": record_id,
                        "from_currency": payload["from_currency"],
                        "to_currency": payload["to_currency"],
                        "rate": payload["rate"],
                        "timestamp": now_utc,
                        "source": payload["source"],
                        "meta": payload.get("meta", {}),
                    })
            except ApiRequestError as exc:
                err_msg = f"Failed to fetch from {name}: {exc}"
                self.logger.error(err_msg)
                errors.append(err_msg)

        if merged_pairs:
            current_pairs.update(merged_pairs)
            new_snapshot = {
                "pairs": current_pairs,
                "last_refresh": now_utc,
            }
            self.storage.save_rates_snapshot(new_snapshot)
            self.storage.append_history(history_records)

            self.logger.info(
                "Writing %d rates to %s...",
                len(merged_pairs),
                self.config.RATES_FILE_PATH,
            )

        return len(merged_pairs), now_utc, errors