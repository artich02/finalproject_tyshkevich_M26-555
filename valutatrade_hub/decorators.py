import functools
from collections.abc import Callable
from typing import Any, TypeVar

from valutatrade_hub.logging_config import setup_logging

F = TypeVar("F", bound=Callable[..., Any])
logger = setup_logging()


def log_action(
    action_name: str,
    verbose: bool = False,
) -> Callable[[F], F]:
    """декоратор логирования"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            service_instance = args[0] if args else None
            username = "unknown"
            if service_instance and hasattr(service_instance, "auth"):
                user = getattr(service_instance.auth, "current_user", None)
                if user:
                    username = getattr(user, "username", "unknown")

            currency = kwargs.get("currency_code")
            if not currency and len(args) > 1:
                currency = args[1]

            amount = kwargs.get("amount")
            if amount is None and len(args) > 2:
                amount = args[2]

            try:
                result = func(*args, **kwargs)
                rate = result.get("rate") if isinstance(result, dict) else None
                rate_str = f" rate={rate:.2f}" if rate is not None else ""
                amount_str = (
                    f" amount={float(amount):.4f}" if amount is not None else ""
                )
                curr_str = f" currency='{currency}'" if currency else ""

                msg = (
                    f"{action_name} user='{username}'{curr_str}{amount_str}"
                    f"{rate_str} base='USD' result=OK"
                )
                if verbose and isinstance(result, dict):
                    before = result.get("before", 0.0)
                    after = result.get("after", 0.0)
                    msg += f" balance_change={before:.4f}->{after:.4f}"

                logger.info(msg)
                return result
            except Exception as exc:
                error_type = exc.__class__.__name__
                curr_str = f" currency='{currency}'" if currency else ""
                msg = (
                    f"{action_name} user='{username}'{curr_str} "
                    f"result=ERROR error_type={error_type} error_msg='{exc}'"
                )
                logger.error(msg)
                raise

        return wrapper

    return decorator