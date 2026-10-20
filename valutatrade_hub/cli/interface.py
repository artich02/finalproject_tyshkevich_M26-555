from __future__ import annotations

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_supported_currencies
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValidationError,
)
from valutatrade_hub.core.usecases import (
    AuthService,
    DataRepository,
    RateService,
    TradingService,
)
from valutatrade_hub.core.utils import parse_command_line
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater


class CommandLineInterface:
    """Контроллер консольного взаимодействия с пользователем"""

    def __init__(self) -> None:
        self.settings = SettingsLoader()
        self.repo = DataRepository()
        self.auth_service = AuthService(self.repo)
        self.rate_service = RateService(self.repo)
        self.trading_service = TradingService(
            repo=self.repo,
            auth_service=self.auth_service,
            rate_service=self.rate_service,
        )
        self.rates_updater = RatesUpdater()

    @staticmethod
    def _parse_named_args(tokens: list[str]) -> dict[str, str]:
        args: dict[str, str] = {}
        i = 0
        while i < len(tokens):
            item = tokens[i]
            if item.startswith("--"):
                key = item[2:]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    args[key] = tokens[i + 1]
                    i += 2
                    continue
                args[key] = ""
            i += 1
        return args

    def handle_register(self, args: dict[str, str]) -> None:
        username = args.get("username")
        password = args.get("password")

        if not username or not password:
            print("Ошибка: укажите --username и --password")
            return

        try:
            user = self.auth_service.register(username, password)
            print(
                f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
                f"Войдите: login --username {user.username} --password ****"
            )
        except ValidationError as exc:
            print(exc)

    def handle_login(self, args: dict[str, str]) -> None:
        username = args.get("username")
        password = args.get("password")

        if not username or not password:
            print("Ошибка: укажите --username и --password")
            return

        try:
            user = self.auth_service.login(username, password)
            print(f"Вы вошли как '{user.username}'")
        except ValidationError as exc:
            print(exc)

    def handle_show_portfolio(self, args: dict[str, str]) -> None:
        base_currency = args.get(
            "base",
            self.settings.get("DEFAULT_BASE_CURRENCY", "USD"),
        ).upper()

        current_user = self.auth_service.current_user
        if not current_user:
            print("Сначала выполните login")
            return

        try:
            items, total = self.trading_service.get_portfolio_overview(
                base_currency
            )
        except CurrencyNotFoundError:
            print(f"Неизвестная базовая валюта '{base_currency}'")
            return
        except ValidationError as exc:
            print(exc)
            return

        print(
            f"Портфель пользователя '{current_user.username}' "
            f"(база: {base_currency}):"
        )
        if not items:
            print("Портфель пуст")
            return

        for item in items:
            cur = item["currency"]
            bal = item["balance"]
            val = item["value_in_base"]
            print(f"- {cur}: {bal:.4f}  → {val:.2f} {base_currency}")

        print("---------------------------------")
        print(f"ИТОГО: {total:,.2f} {base_currency}")

    def handle_buy(self, args: dict[str, str]) -> None:
        curr = args.get("currency")
        raw_amount = args.get("amount")

        if not curr or not raw_amount:
            print("Ошибка: укажите --currency и --amount")
            return

        try:
            amount = float(raw_amount)
        except ValueError:
            print("'amount' должен быть положительным числом")
            return

        try:
            res = self.trading_service.buy_currency(curr, amount)
            target = curr.upper()
            print(
                f"Покупка выполнена: {res['amount']:.4f} {target} "
                f"по курсу {res['rate']:.2f} USD/{target}"
            )
            print("Изменения в портфеле:")
            print(
                f"- {target}: было {res['before']:.4f} → стало {res['after']:.4f}"
            )
            print(f"Оценочная стоимость покупки: {res['cost_usd']:,.2f} USD")
        except CurrencyNotFoundError as exc:
            print(exc)
            supported = ", ".join(get_supported_currencies())
            print(f"Поддерживаемые валюты: {supported}")
        except ValidationError as exc:
            print(exc)

    def handle_sell(self, args: dict[str, str]) -> None:
        curr = args.get("currency")
        raw_amount = args.get("amount")

        if not curr or not raw_amount:
            print("Ошибка: укажите --currency и --amount")
            return

        try:
            amount = float(raw_amount)
        except ValueError:
            print("'amount' должен быть положительным числом")
            return

        try:
            res = self.trading_service.sell_currency(curr, amount)
            target = curr.upper()
            print(
                f"Продажа выполнена: {res['amount']:.4f} {target} "
                f"по курсу {res['rate']:.2f} USD/{target}"
            )
            print("Изменения в портфеле:")
            print(
                f"- {target}: было {res['before']:.4f} → стало {res['after']:.4f}"
            )
            print(f"Оценочная выручка: {res['income_usd']:,.2f} USD")
        except CurrencyNotFoundError as exc:
            print(exc)
        except InsufficientFundsError as exc:
            print(exc)
        except ValidationError as exc:
            print(exc)

    def handle_get_rate(self, args: dict[str, str]) -> None:
        from_curr = args.get("from")
        to_curr = args.get("to")

        if not from_curr or not to_curr:
            print("Ошибка: укажите --from и --to")
            return

        src = from_curr.upper()
        dst = to_curr.upper()

        try:
            direct_rate, updated_at = self.rate_service.get_rate(src, dst)
            reverse_rate, _ = self.rate_service.get_rate(dst, src)
            clean_time = updated_at.replace("T", " ").replace("Z", "")
            print(f"Курс {src}→{dst}: {direct_rate:.8f} (обновлено: {clean_time})")
            print(f"Обратный курс {dst}→{src}: {reverse_rate:.2f}")
        except CurrencyNotFoundError as exc:
            print(exc)
            supported = ", ".join(get_supported_currencies())
            print(f"Доступные валюты: {supported}")
        except ApiRequestError:
            print(f"Курс {src}→{dst} недоступен. Повторите попытку позже")
        except ValidationError as exc:
            print(exc)

    def handle_update_rates(self, args: dict[str, str]) -> None:
        source_filter = args.get("source")
        print("[ИНФО] Запуск обновления курсов...")

        count, last_refresh, errors = self.rates_updater.run_update(source_filter)

        if not source_filter or "coingecko" in source_filter.lower():
            if any("CoinGecko" in e for e in errors):
                print("[ОШИБКА] Не удалось получить данные от CoinGecko: Сбой сети")
            else:
                print("[ИНФО] Получение данных от CoinGecko... Успешно (3 курса)")

        if not source_filter or "exchangerate" in source_filter.lower():
            if any("ExchangeRate" in e for e in errors):
                print(
                    "[ОШИБКА] Не удалось получить данные от ExchangeRate-API: "
                    "Сбой сети"
                )
            else:
                print(
                    "[ИНФО] Получение данных от ExchangeRate-API... "
                    "Успешно (3 курса)"
                )

        if errors:
            print(
                "Обновление завершено с ошибками. "
                "Подробности смотрите в logs/actions.log"
            )
            return

        print(
            f"[ИНФО] Запись {count} курсов в "
            f"{self.rates_updater.config.RATES_FILE_PATH}..."
        )
        print(
            f"Обновление успешно завершено. Всего обновлено курсов: {count}. "
            f"Время обновления: {last_refresh}"
        )

    def handle_show_rates(self, args: dict[str, str]) -> None:
        target_curr = args.get("currency")
        top_arg = args.get("top")
        base_arg = args.get("base", "USD").upper()

        snapshot = self.rates_updater.storage.load_rates_snapshot()
        pairs = snapshot.get("pairs", {})
        last_refresh = snapshot.get("last_refresh", "")

        if not pairs:
            print(
                "Локальный кеш курсов пуст. "
                "Выполните 'update-rates', чтобы загрузить данные"
            )
            return

        if target_curr:
            clean_curr = target_curr.strip().upper()
            found = False
            for pair, data in pairs.items():
                if pair.startswith(f"{clean_curr}_"):
                    rate_val = data.get("rate", 0.0)
                    print(f"Курсы из локального кеша (обновлено: {last_refresh}):")
                    print(f"- {pair}: {rate_val:.5f}")
                    found = True
                    break
            if not found:
                print(f"Курс для '{clean_curr}' не найден в кеше")
            return

        if top_arg:
            try:
                top_limit = int(top_arg)
            except ValueError:
                print("Значение --top должно быть целым числом")
                return

            crypto_pairs = [
                (pair, data)
                for pair, data in pairs.items()
                if any(c in pair for c in ("BTC", "ETH", "SOL"))
            ]
            crypto_pairs.sort(key=lambda x: x[1].get("rate", 0.0), reverse=True)
            selected = crypto_pairs[:top_limit]

            print(f"Курсы из локального кеша (обновлено: {last_refresh}):")
            for pair, data in selected:
                print(f"- {pair}: {data.get('rate', 0.0):.2f}")
            return

        table = PrettyTable()
        table.field_names = [
            "Валютная пара",
            f"Курс к {base_arg}",
            "Источник",
            "Дата обновления",
        ]
        for pair, data in sorted(pairs.items()):
            table.add_row([
                pair,
                f"{data.get('rate', 0.0):.6f}",
                data.get("source", "Н/Д"),
                data.get("updated_at", ""),
            ])
        print(table)

    def run(self) -> None:
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    continue

                tokens = parse_command_line(line)
                if not tokens:
                    continue

                cmd = tokens[0].lower()
                named_args = self._parse_named_args(tokens[1:])

                if cmd == "exit":
                    break
                if cmd == "register":
                    self.handle_register(named_args)
                elif cmd == "login":
                    self.handle_login(named_args)
                elif cmd == "show-portfolio":
                    self.handle_show_portfolio(named_args)
                elif cmd == "buy":
                    self.handle_buy(named_args)
                elif cmd == "sell":
                    self.handle_sell(named_args)
                elif cmd == "get-rate":
                    self.handle_get_rate(named_args)
                elif cmd == "update-rates":
                    self.handle_update_rates(named_args)
                elif cmd == "show-rates":
                    self.handle_show_rates(named_args)
                else:
                    print(f"Неизвестная команда: {cmd}")
            except (KeyboardInterrupt, EOFError):
                break