from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Any

from valutatrade_hub.core.constants import (
    DEFAULT_BASE_CURRENCY,
    DEFAULT_EXCHANGE_RATES,
    FLOAT_ROUND_DIGITS,
    MIN_PASSWORD_LENGTH,
    SALT_BYTES_LENGTH,
)
from valutatrade_hub.core.exceptions import (
    CurrencyAlreadyExistsError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValidationError,
)


class User:
    """Модель пользователя"""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str | None = None,
        hashed_password: str | None = None,
        salt: str | None = None,
        registration_date: datetime | str | None = None,
    ) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("user_id должен быть положительным целым числом")

        self._user_id: int = user_id
        self._username: str = ""
        self.username = username  # Валидация через сеттер

        if registration_date is None:
            self._registration_date: datetime = datetime.now()
        elif isinstance(registration_date, str):
            self._registration_date = datetime.fromisoformat(registration_date)
        elif isinstance(registration_date, datetime):
            self._registration_date = registration_date
        else:
            raise ValidationError("Неверный формат даты регистрации")

        if hashed_password and salt:
            self._salt = salt
            self._hashed_password = hashed_password
        elif password:
            self._salt = secrets.token_hex(SALT_BYTES_LENGTH)
            self._hashed_password = self._hash_password(password, self._salt)
        else:
            raise ValidationError("Необходимо передать либо пароль, либо хеш и соль")

    @staticmethod
    def _hash_password(raw_password: str, salt: str) -> str:
        """Односторонний хеш пароля с солью через SHA-256"""
        salted = f"{raw_password}{salt}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    def verify_password(self, password: str) -> bool:
        """проверка пароля на совпадение"""
        if not isinstance(password, str):
            return False
        candidate_hash = self._hash_password(password, self._salt)
        return secrets.compare_digest(candidate_hash, self._hashed_password)

    def change_password(self, new_password: str) -> None:
        """смена пароля"""
        if (
            not isinstance(new_password, str)
            or len(new_password) < MIN_PASSWORD_LENGTH
        ):
            msg = f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
            raise ValidationError(msg)
        self._salt = secrets.token_hex(SALT_BYTES_LENGTH)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def get_user_info(self) -> dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=data["registration_date"],
        )


class Wallet:
    """Модель кошелька"""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValidationError("Код валюты должен быть непустой строкой")

        self.currency_code: str = currency_code.strip().upper()
        self._balance: float = 0.0
        self.balance = balance  # Валидация через сеттер

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float | int) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationError("Баланс должен быть числовым значением")
        if value < 0:
            raise ValidationError("Баланс не может быть отрицательным")
        self._balance = round(float(value), FLOAT_ROUND_DIGITS)

    def deposit(self, amount: float | int) -> None:
        """пополнение баланса"""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("Сумма пополнения должна быть строго больше нуля")
        self.balance += amount

    def withdraw(self, amount: float | int) -> None:
        """снятие средств с баланса"""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("Сумма снятия должна быть строго больше нуля")
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=float(amount),
                code=self.currency_code,
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        """Форматированный вывод баланса"""
        return f"{self.currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, Any]:
        """Сериализация данных кошелька"""
        return {"balance": self._balance}


class Portfolio:
    """Управление портфелем"""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("user_id должен быть положительным целым числом")

        self._user_id: int = user_id
        self._user: User | None = user
        self._wallets: dict[str, Wallet] = {}

        if wallets:
            for code, wallet in wallets.items():
                if not isinstance(wallet, Wallet):
                    msg = "Все элементы словаря должны быть объектами Wallet"
                    raise ValidationError(msg)
                self._wallets[code.upper()] = wallet

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User | None:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str, initial_balance: float = 0.0) -> Wallet:
        """Добавление новой валюты"""
        code = currency_code.strip().upper()
        if code in self._wallets:
            msg = f"Кошелек с валютой {code} уже существует"
            raise CurrencyAlreadyExistsError(msg)

        new_wallet = Wallet(currency_code=code, balance=initial_balance)
        self._wallets[code] = new_wallet
        return new_wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """получение объекта кошелька по коду валюты"""
        code = currency_code.strip().upper()
        wallet = self._wallets.get(code)
        if not wallet:
            raise CurrencyNotFoundError(code)
        return wallet

    def get_total_value(
        self,
        base_currency: str = DEFAULT_BASE_CURRENCY,
        rates: dict[str, float] | None = None,
    ) -> float:
        """Расчет общей стоимости портфеля"""
        current_rates = rates if rates is not None else DEFAULT_EXCHANGE_RATES
        target_currency = base_currency.strip().upper()

        if target_currency not in current_rates:
            msg = f"Отсутствует курс для базовой валюты {target_currency}"
            raise ValidationError(msg)

        base_in_usd = current_rates[target_currency]
        if base_in_usd <= 0:
            raise ValidationError("Курс базовой валюты должен быть положительным")

        total_in_usd = 0.0
        for code, wallet in self._wallets.items():
            if code not in current_rates:
                msg = f"Не найден курс для валюты {code} в расчете портфеля"
                raise ValidationError(msg)
            rate_to_usd = current_rates[code]
            total_in_usd += wallet.balance * rate_to_usd

        return round(total_in_usd / base_in_usd, 4)

    def to_dict(self) -> dict[str, Any]:
        """сериализация портфеля"""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict() for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], user: User | None = None) -> Portfolio:
        """десериализация портфеля из словаря"""
        wallets_dict: dict[str, Wallet] = {}
        for code, payload in data.get("wallets", {}).items():
            wallets_dict[code.upper()] = Wallet(
                currency_code=code.upper(),
                balance=payload.get("balance", 0.0),
            )

        return cls(
            user_id=data["user_id"],
            wallets=wallets_dict,
            user=user,
        )