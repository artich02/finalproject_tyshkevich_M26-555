import functools
import shlex
import sys
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def log_action_time(func: F) -> F:
    """декоратор для замера и вывода времени выполнения функции"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        print(f"[LOG] Действие {func.__name__} выполнено за {elapsed:.4f} сек")
        return result

    return wrapper  # type: ignore[return-value]


def confirm_action(prompt_message: str = "Хотите продолжить?") -> Callable[[F], F]:
    """декоратор запроса подтверждения пользователя перед выполнением операции"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            answer = input(f"{prompt_message} (y/n): ").strip().lower()
            if answer not in ("y", "yes", "да", "д"):
                print("[INFO] Операция отменена пользователем")
                return None
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def create_rate_cache(ttl_seconds: int = 60) -> tuple[Callable[[], Any], 
                                                      Callable[[Any], None]]:
    """Замыкание для кэширования курсов валют с ограничением по времени"""
    cached_data: Any = None
    last_updated: float = 0.0

    def get_cache() -> Any:
        nonlocal cached_data, last_updated
        if cached_data is not None and (time.time() - last_updated) < ttl_seconds:
            return cached_data
        return None

    def set_cache(data: Any) -> None:
        nonlocal cached_data, last_updated
        cached_data = data
        last_updated = time.time()

    return get_cache, set_cache


def parse_command_line(cmd_line: str) -> list[str]:
    """безопасный разбор строки ввода на токены с поддержкой платформ Unix и Windows"""
    if not cmd_line.strip():
        return []

    is_posix = sys.platform != "win32"
    try:
        return shlex.split(cmd_line, posix=is_posix)
    except ValueError:
        return cmd_line.split()