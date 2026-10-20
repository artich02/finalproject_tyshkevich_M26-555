import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


@dataclass(frozen=True)
class ParserConfig:
    """Параметры и эндпоинты внешних источников"""

    #персональный API ключ ExchangeRate-API (с fallback на дефолтный)
    EXCHANGERATE_API_KEY: str = os.getenv(
        "EXCHANGERATE_API_KEY",
        "f7bb591b79b9d681005c5079",
    )

    #Внешние эндпоинты
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    #базовые валюты
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")

    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    #Пути к файлам
    RATES_FILE_PATH: Path = field(
        default_factory=lambda: SettingsLoader().get("RATES_FILE")
    )
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: (
            SettingsLoader().get("DATA_DIR") / "exchange_rates.json"
        )
    )

    #таймаут
    REQUEST_TIMEOUT: int = 10