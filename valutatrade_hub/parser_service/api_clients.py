from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        """возвращает словарь пар"""


class CoinGeckoClient(BaseApiClient):
    """Клиент для обращения к публичному API"""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        ids_param = ",".join(self.config.CRYPTO_ID_MAP.values())
        params = {
            "ids": ids_param,
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        headers = {"User-Agent": "ValutaTradeHub/1.0"}

        start_time = time.perf_counter()
        try:
            resp = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 429:
                raise ApiRequestError("CoinGecko: лимит запросов исчерпан (429)")
            if resp.status_code != 200:
                msg = f"CoinGecko: код статуса {resp.status_code}"
                raise ApiRequestError(msg)

            data = resp.json()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"Ошибка сети CoinGecko: {exc}") from exc

        rates: dict[str, dict[str, Any]] = {}
        target_field = self.config.BASE_CURRENCY.lower()

        for code, coin_id in self.config.CRYPTO_ID_MAP.items():
            if coin_id in data and target_field in data[coin_id]:
                rate_val = float(data[coin_id][target_field])
                pair_key = f"{code}_{self.config.BASE_CURRENCY}"
                rates[pair_key] = {
                    "from_currency": code,
                    "to_currency": self.config.BASE_CURRENCY,
                    "rate": rate_val,
                    "source": "CoinGecko",
                    "meta": {
                        "raw_id": coin_id,
                        "request_ms": elapsed_ms,
                        "status_code": resp.status_code,
                        "etag": resp.headers.get("ETag", ""),
                    },
                }

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """клиент для обращения к ExchangeRate"""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )

        start_time = time.perf_counter()
        try:
            resp = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 429:
                raise ApiRequestError("ExchangeRate-API: лимит запросов исчерпан")
            if resp.status_code != 200:
                msg = f"ExchangeRate-API: код статуса {resp.status_code}"
                raise ApiRequestError(msg)

            data = resp.json()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"Ошибка сети ExchangeRate-API: {exc}") from exc

        if data.get("result") != "success":
            error_type = data.get("error-type", "неизвестная ошибка")
            raise ApiRequestError(f"ExchangeRate-API отклонил запрос: {error_type}")

        raw_rates = data.get("conversion_rates") or data.get("rates", {})
        rates: dict[str, dict[str, Any]] = {}

        for code in self.config.FIAT_CURRENCIES:
            if code in raw_rates:
                val = float(raw_rates[code])
                rate_in_usd = round(1.0 / val, 6) if val > 0 else 0.0
                pair_key = f"{code}_{self.config.BASE_CURRENCY}"
                rates[pair_key] = {
                    "from_currency": code,
                    "to_currency": self.config.BASE_CURRENCY,
                    "rate": rate_in_usd,
                    "source": "ExchangeRate-API",
                    "meta": {
                        "raw_id": code.lower(),
                        "request_ms": elapsed_ms,
                        "status_code": resp.status_code,
                        "etag": resp.headers.get("ETag", ""),
                    },
                }

        return rates