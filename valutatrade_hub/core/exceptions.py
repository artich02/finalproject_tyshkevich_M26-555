class ValutaTradeError(Exception):
    """базовое исключение проекта"""


class ValidationError(ValutaTradeError):
    """Ошибка валидации входных данных"""


class InsufficientFundsError(ValutaTradeError):
    """Нехватка средств на балансе кошелька"""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        msg = (
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )
        super().__init__(msg)


class CurrencyNotFoundError(ValutaTradeError):
    """Запрос незарегистрированной валюты"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class CurrencyAlreadyExistsError(ValutaTradeError):
    """Исключение при попытке повторного добавления валюты в портфель"""


class ApiRequestError(ValutaTradeError):
    """Ошибка при обращении к внешнему API или парсеру курсов"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")