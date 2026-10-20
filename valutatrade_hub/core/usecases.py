from __future__ import annotations

from datetime import datetime
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InsufficientFundsError,
    ValidationError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import create_rate_cache
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class DataRepository:
    """Репозиторий работы с сущностями через DatabaseManager Singleton"""

    def __init__(self) -> None:
        self.db = DatabaseManager()

    def load_users(self) -> list[User]:
        raw = self.db.read_json(self.db.users_file)
        return [User.from_dict(item) for item in raw] if isinstance(raw, list) else []

    def save_users(self, users: list[User]) -> None:
        self.db.write_json(self.db.users_file, [u.to_dict() for u in users])

    def load_portfolios(self) -> list[Portfolio]:
        raw = self.db.read_json(self.db.portfolios_file)
        return [Portfolio.from_dict(p) for p in raw] if isinstance(raw, list) else []

    def save_portfolios(self, portfolios: list[Portfolio]) -> None:
        self.db.write_json(self.db.portfolios_file, [p.to_dict() for p in portfolios])

    def load_rates_data(self) -> dict[str, Any]:
        raw = self.db.read_json(self.db.rates_file)
        return raw if isinstance(raw, dict) else {}

    def save_rates_data(self, data: dict[str, Any]) -> None:
        self.db.write_json(self.db.rates_file, data)


class AuthService:
    """Регистрация и аутентификация пользователей"""

    def __init__(self, repo: DataRepository) -> None:
        self.repo = repo
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        return self._current_user

    def is_authenticated(self) -> bool:
        return self._current_user is not None

    def register(self, username: str, password: str) -> User:
        clean_name = username.strip()
        if not clean_name:
            raise ValidationError("Имя пользователя не может быть пустым")

        if len(password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов")

        users = self.repo.load_users()
        if any(u.username.lower() == clean_name.lower() for u in users):
            raise ValidationError(f"Имя пользователя '{clean_name}' уже занято")

        new_id = max((u.user_id for u in users), default=0) + 1
        new_user = User(user_id=new_id, username=clean_name, password=password)
        users.append(new_user)
        self.repo.save_users(users)

        portfolios = self.repo.load_portfolios()
        portfolios.append(Portfolio(user_id=new_id, wallets={}))
        self.repo.save_portfolios(portfolios)
        return new_user

    def login(self, username: str, password: str) -> User:
        clean_name = username.strip()
        users = self.repo.load_users()
        user = next(
            (u for u in users if u.username.lower() == clean_name.lower()),
            None,
        )
        if not user:
            raise ValidationError(f"Пользователь '{clean_name}' не найден")

        if not user.verify_password(password):
            raise ValidationError("Неверный пароль")

        self._current_user = user
        return user

    def logout(self) -> None:
        self._current_user = None


class RateService:
    """сервис котировок"""

    def __init__(self, repo: DataRepository) -> None:
        self.repo = repo
        settings = SettingsLoader()
        ttl: int = settings.get("RATES_TTL_SECONDS", 300)
        self._get_cache, self._set_cache = create_rate_cache(ttl_seconds=ttl)

    def get_rate(self, from_curr: str, to_curr: str) -> tuple[float, str]:
        """Актуальный курс валютной пары"""
        src_curr = get_currency(from_curr)
        dst_curr = get_currency(to_curr)

        rates_data = self._get_cache()
        if rates_data is None:
            rates_data = self.repo.load_rates_data()
            if not rates_data:
                raise ApiRequestError("Локальный кеш котировок пуст")
            self._set_cache(rates_data)

        def resolve_usd_rate(code: str) -> tuple[float, str]:
            if code == "USD":
                return 1.0, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            pair_key = f"{code}_USD"
            pairs_dict = rates_data.get("pairs", rates_data)

            if pair_key in pairs_dict and "rate" in pairs_dict[pair_key]:
                return (
                    float(pairs_dict[pair_key]["rate"]),
                    pairs_dict[pair_key].get("updated_at", ""),
                )
            raise ApiRequestError(f"Курс для {code}USD не найден в кеше")

        src_usd, updated_at = resolve_usd_rate(src_curr.code)
        dst_usd, _ = resolve_usd_rate(dst_curr.code)

        calculated_rate = src_usd / dst_usd
        return calculated_rate, updated_at


class TradingService:
    """Сервис торговых операций"""

    def __init__(
        self,
        repo: DataRepository,
        auth_service: AuthService,
        rate_service: RateService,
    ) -> None:
        self.repo = repo
        self.auth = auth_service
        self.rates = rate_service

    def _get_current_portfolio(self) -> Portfolio:
        if not self.auth.is_authenticated() or not self.auth.current_user:
            raise ValidationError("Сначала выполните login")

        user_id = self.auth.current_user.user_id
        portfolios = self.repo.load_portfolios()
        for p in portfolios:
            if p.user_id == user_id:
                return p

        new_p = Portfolio(user_id=user_id, wallets={})
        portfolios.append(new_p)
        self.repo.save_portfolios(portfolios)
        return new_p

    def _save_portfolio(self, portfolio: Portfolio) -> None:
        portfolios = self.repo.load_portfolios()
        updated = [p for p in portfolios if p.user_id != portfolio.user_id]
        updated.append(portfolio)
        self.repo.save_portfolios(updated)

    def get_portfolio_overview(
        self,
        base_currency: str = "USD",
    ) -> tuple[list[dict[str, Any]], float]:
        portfolio = self._get_current_portfolio()
        base_curr = get_currency(base_currency)

        items: list[dict[str, Any]] = []
        total_value = 0.0

        for code, wallet in portfolio.wallets.items():
            rate, _ = self.rates.get_rate(code, base_curr.code)
            val_in_base = wallet.balance * rate
            total_value += val_in_base
            items.append({
                "currency": code,
                "balance": wallet.balance,
                "value_in_base": val_in_base,
            })

        return items, total_value

    @log_action(action_name="BUY", verbose=True)
    def buy_currency(
        self,
        currency_code: str,
        amount: float,
    ) -> dict[str, float]:
        """покупка валюты"""
        if not self.auth.is_authenticated():
            raise ValidationError("Сначала выполните login")

        if amount <= 0:
            raise ValidationError("'amount' должен быть положительным числом")

        target = get_currency(currency_code).code
        rate_to_usd, _ = self.rates.get_rate(target, "USD")
        portfolio = self._get_current_portfolio()

        if target not in portfolio.wallets:
            wallet = portfolio.add_currency(target)
            before_balance = 0.0
        else:
            wallet = portfolio.get_wallet(target)
            before_balance = wallet.balance

        wallet.deposit(amount)
        self._save_portfolio(portfolio)

        return {
            "amount": amount,
            "rate": rate_to_usd,
            "before": before_balance,
            "after": wallet.balance,
            "cost_usd": amount * rate_to_usd,
        }

    @log_action(action_name="SELL", verbose=True)
    def sell_currency(
        self,
        currency_code: str,
        amount: float,
    ) -> dict[str, float]:
        """Продажа валюты"""
        if not self.auth.is_authenticated():
            raise ValidationError("Сначала выполните login")

        if amount <= 0:
            raise ValidationError("'amount' должен быть положительным числом")

        target = get_currency(currency_code).code
        portfolio = self._get_current_portfolio()

        if target not in portfolio.wallets:
            msg = (
                f"У вас нет кошелька '{target}'. "
                "Добавьте валюту: она создаётся автоматически при первой покупке"
            )
            raise ValidationError(msg)

        wallet = portfolio.get_wallet(target)
        if wallet.balance < amount:
            raise InsufficientFundsError(
                available=wallet.balance,
                required=amount,
                code=target,
            )

        rate_to_usd, _ = self.rates.get_rate(target, "USD")
        before_balance = wallet.balance
        wallet.withdraw(amount)
        self._save_portfolio(portfolio)

        return {
            "amount": amount,
            "rate": rate_to_usd,
            "before": before_balance,
            "after": wallet.balance,
            "income_usd": amount * rate_to_usd,
        }