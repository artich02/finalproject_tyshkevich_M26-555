### finalproject_tyshkevich_M26-555

# ValutaTrade Hub

Комплексная консольная платформа виртуального трейдинга.

## Основные возможности

- **Управление профилем**: Регистрация с односторонним хешированием пароля (SHA-256 + уникальная соль), авторизация и сессии.
- **Виртуальный портфель**: Мультивалютные кошельки, автосоздание кошельков при первой покупке, расчет суммарной стоимости активов в любой базовой валюте.
- **Торговые операции**: Покупка и продажа валют с валидацией остатков и контролем баланса.
- **Parser Service**: Автономный сбор котировок из внешних API, атомарная запись данных и ведение исторического журнала измерений.
- **Кэширование**: Контроль актуальности котировок через замыкания (TTL 5 минут).
- **Надежность**: Логирование доменных событий с ротацией файлов (`logs/actions.log`), строгие пользовательские исключения.

## Архитектура проекта

```text
finalproject_<фамилия>_<группа>/
├── data/
│    ├── users.json             # Реестр пользователей
│    ├── portfolios.json        # Портфели и балансы кошельков
│    ├── rates.json             # Локальный срез актуальных курсов
│    └── exchange_rates.json    # Исторический журнал котировок парсера
├── logs/
│    └── actions.log            # Журнал действий с ротацией
├── valutatrade_hub/
│    ├── core/
│    │    ├── constants.py      # Глобальные константы
│    │    ├── currencies.py     # Иерархия валют (Fiat/Crypto) и реестр
│    │    ├── exceptions.py     # Доменные исключения
│    │    ├── models.py         # Модели User, Wallet, Portfolio
│    │    ├── usecases.py       # Бизнес-логика (Auth, Trading, Rates)
│    │    └── utils.py          # Декораторы, замыкания и парсер строк
│    ├── infra/
│    │    ├── settings.py       # Singleton SettingsLoader
│    │    └── database.py       # Singleton DatabaseManager
│    ├── parser_service/
│    │    ├── config.py         # Конфигурация внешних API
│    │    ├── api_clients.py    # Клиенты CoinGecko и ExchangeRate-API
│    │    ├── updater.py        # Координатор синхронизации
│    │    ├── storage.py        # Атомарное файловое хранилище
│    │    └── scheduler.py      # Фоновый планировщик
│    ├── cli/
│    │    └── interface.py      # Пользовательский консольный интерфейс
│    ├── decorators.py          # Декоратор @log_action
│    └── logging_config.py      # Настройка RotatingFileHandler
├── main.py                     # Точка входа
├── pyproject.toml              # Конфигурация проекта и зависимостей uv
├── .gitignore
└── README.md
```

## Запуск проекта

```text
uv run python main.py
```


## Примеры команд


### Регистрация нового пользователя:
```text
register --username alice --password 1234
```

### Вход в систему:
```text
login --username alice --password 1234
```

### Обновление курсов через внешние API:
```text
update-rates
```

### Просмотр таблицы котировок:
```text
show-rates
show-rates --top 2
show-rates --currency BTC
```

### Получение курса валютной пары:
```text
get-rate --from USD --to BTC
```

### Покупка валюты:
```text
buy --currency BTC --amount 0.05
```

### Продажа валюты:
```text
sell --currency BTC --amount 0.01
```

### Просмотр портфеля:
```text
show-portfolio
show-portfolio --base EUR
```

### Выход из приложения:
```text
exit
```