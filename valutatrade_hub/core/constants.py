from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DATA_DIR: Path = BASE_DIR / "data"

USERS_FILE: Path = DATA_DIR / "users.json"
PORTFOLIOS_FILE: Path = DATA_DIR / "portfolios.json"
RATES_FILE: Path = DATA_DIR / "rates.json"

MIN_PASSWORD_LENGTH: int = 4
SALT_BYTES_LENGTH: int = 8
FLOAT_ROUND_DIGITS: int = 8
FIAT_ROUND_DIGITS: int = 4

DEFAULT_BASE_CURRENCY: str = "USD"
RATE_CACHE_TTL_SECONDS: int = 300  # 5минут

DEFAULT_EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.0786,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.0,
}

DEFAULT_PAIR_RATES: dict[str, float] = {
    "USD_USD": 1.0,
    "EUR_USD": 1.0786,
    "BTC_USD": 59337.21,
    "RUB_USD": 0.01016,
    "ETH_USD": 3720.0,
}