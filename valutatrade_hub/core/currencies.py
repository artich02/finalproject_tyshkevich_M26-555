from __future__ import annotations

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError, ValidationError


class Currency(ABC):
    """Абстрактный базовый класс валюты"""

    def __init__(self, name: str, code: str) -> None:
        if not isinstance(code, str) or not (2 <= len(code.strip()) <= 5):
            msg = "Код валюты должен содержать от 2 до 5 символов"
            raise ValidationError(msg)

        clean_code = code.strip().upper()
        if " " in clean_code:
            msg = "Код валюты не должен содержать пробелов"
            raise ValidationError(msg)

        if not isinstance(name, str) or not name.strip():
            msg = "Имя валюты не может быть пустым"
            raise ValidationError(msg)

        self.name: str = name.strip()
        self.code: str = clean_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление валюты"""


class FiatCurrency(Currency):

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            msg = "Страна эмиссии не может быть пустой строкой"
            raise ValidationError(msg)
        self.issuing_country: str = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float = 0.0,
    ) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            msg = "Алгоритм не может быть пустым"
            raise ValidationError(msg)
        self.algorithm: str = algorithm.strip()
        self.market_cap: float = max(0.0, float(market_cap))

    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}"
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {mcap_str})"
        )


# Реестр валют
_CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "PoS", 4.20e11),
    "SOL": CryptoCurrency("Solana", "SOL", "PoH", 6.80e10),
}


def get_currency(code: str) -> Currency:
    """получение объекта валюты по её коду"""
    clean_code = code.strip().upper() if isinstance(code, str) else ""
    currency = _CURRENCY_REGISTRY.get(clean_code)
    if not currency:
        raise CurrencyNotFoundError(clean_code)
    return currency


def get_supported_currencies() -> list[str]:
    """список всех зарегистрированных кодов валют"""
    return list(_CURRENCY_REGISTRY.keys())