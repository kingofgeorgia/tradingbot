# Binance Spot Trading Bot

[![CI](https://github.com/kingofgeorgia/tradingbot/actions/workflows/ci.yml/badge.svg)](https://github.com/kingofgeorgia/tradingbot/actions/workflows/ci.yml)
[![Run Bot Once](https://github.com/kingofgeorgia/tradingbot/actions/workflows/run-bot.yml/badge.svg)](https://github.com/kingofgeorgia/tradingbot/actions/workflows/run-bot.yml)

Локальный торговый бот для Binance Spot на Python 3.11+ с EMA crossover стратегией, встроенным риск-менеджментом, журналированием и Telegram-уведомлениями.

## Что умеет

- `APP_MODE=demo` для Binance Spot Testnet и `APP_MODE=live` для production.
- Торговля по списку инструментов из `SYMBOLS`, по умолчанию `BTCUSDT,ETHUSDT`.
- Таймфрейм `15m` и стратегия на пересечении `EMA(20)` и `EMA(50)`.
- Локальный `stop-loss` и `take-profit`.
- Ограничения риска: лимит риска на сделку, размер позиции, число одновременно открытых позиций, дневной лимит убытка и блокировка после серии убытков.
- Логи в консоль и файлы, CSV-журналы сигналов, сделок и ошибок.
- Telegram-уведомления о старте, сделках, API-ошибках и остановке торговли.

## Архитектура

- `main.py` — точка входа, добавляет `src` в `PYTHONPATH` и запускает бота.
- `src/binance_bot/config.py` — загрузка `.env`, валидация настроек и подготовка runtime-директорий.
- `src/binance_bot/clients/binance_client.py` — REST-клиент Binance Spot.
- `src/binance_bot/strategy/ema_cross.py` — вычисление EMA и генерация сигналов.
- `src/binance_bot/risk/manager.py` — риск-менеджмент и лимиты торговли.
- `src/binance_bot/orders/manager.py` — открытие и закрытие позиций.
- `src/binance_bot/notify/telegram.py` — уведомления в Telegram.
- `src/binance_bot/core/` — модели, state store, логирование и CSV-журналы.

## Быстрый старт

1. Установите Python 3.11+.
2. Создайте виртуальное окружение.

```bash
python -m venv .venv
```

3. Активируйте окружение и установите зависимости.

```bash
pip install -r requirements.txt
```

4. Создайте локальный `.env` на основе шаблона.

```bash
cp .env.example .env
```

5. Заполните ключи Binance и при необходимости Telegram.
6. Для безопасного старта используйте `APP_MODE=demo` и ключи Binance Spot Testnet.
7. Запустите бота.

```bash
python main.py
```

## Переменные окружения

| Переменная | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `APP_MODE` | `demo` для Testnet или `live` для production | `demo` |
| `BINANCE_API_KEY` | Binance API key | обязательна |
| `BINANCE_SECRET_KEY` | Binance secret key | обязательна |
| `BINANCE_RECV_WINDOW` | окно подтверждения запроса Binance | `5000` |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота | пусто |
| `TELEGRAM_CHAT_ID` | чат для уведомлений | пусто |
| `SYMBOLS` | список торговых пар через запятую | `BTCUSDT,ETHUSDT` |
| `TIMEFRAME` | таймфрейм стратегии | `15m` |
| `CANDLE_LIMIT` | число свечей на вход стратегии | `120` |
| `FAST_EMA_PERIOD` | быстрый EMA period | `20` |
| `SLOW_EMA_PERIOD` | медленный EMA period | `50` |
| `STOP_LOSS_PCT` | stop-loss в долях | `0.02` |
| `TAKE_PROFIT_PCT` | take-profit в долях | `0.04` |
| `RISK_PER_TRADE_PCT` | риск на сделку от equity | `0.01` |
| `MAX_POSITION_PCT` | максимум капитала на позицию | `0.10` |
| `MAX_OPEN_POSITIONS_TOTAL` | общий лимит открытых позиций | `2` |
| `MAX_OPEN_POSITIONS_PER_SYMBOL` | лимит позиций на инструмент | `1` |
| `DAILY_LOSS_LIMIT_PCT` | дневной лимит убытка | `0.03` |
| `MAX_CONSECUTIVE_LOSSES` | остановка после серии убыточных сделок | `3` |
| `LOOP_INTERVAL_SECONDS` | пауза между циклами | `30` |
| `ORDER_CONFIRM_TIMEOUT_SECONDS` | ожидание подтверждения ордера | `15` |
| `REQUEST_TIMEOUT_SECONDS` | таймаут HTTP-запросов | `15` |
| `STALE_DATA_MULTIPLIER` | множитель допустимой давности свечи | `2` |
| `QUOTE_ASSET` | котируемый актив портфеля | `USDT` |
| `RUN_ONCE` | выполнить один цикл и завершиться | `false` |

## Безопасность и секреты

- `.env` и другие локальные env-файлы исключены из git.
- В репозиторий коммитится только `.env.example` с пустыми или тестовыми значениями.
- Не включайте права на вывод средств для Binance API-ключей.
- Перед `APP_MODE=live` прогоняйте бота в `demo` и проверяйте журналы.
- В текущей версии stop-loss и take-profit контролируются ботом локально, а не серверными OCO-ордерами.

## GitHub Actions

В репозитории настроены два workflow.

### CI

Файл `.github/workflows/ci.yml` запускается на `push` и `pull_request` и выполняет:

- установку зависимостей;
- `python -m compileall main.py src tests`;
- unit-тесты для стратегии и риск-менеджмента;
- проверку, что конфигурация корректно загружается с ожидаемыми env-переменными.

### Run Bot Once

Файл `.github/workflows/run-bot.yml` запускается вручную через `workflow_dispatch` и:

- поднимает Python 3.11;
- читает секреты из GitHub Secrets;
- принудительно выставляет `RUN_ONCE=true`;
- выполняет один цикл бота;
- сохраняет `logs/` и `data/` как artifacts.

Это безопаснее, чем пытаться держать торгового бота постоянно работающим в GitHub Actions. Для круглосуточной торговли используйте VPS, Docker-хост или выделенный сервер.

## GitHub Secrets

Для workflow `Run Bot Once` добавьте secrets с такими именами:

- `BINANCE_API_KEY`
- `BINANCE_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Если workflow должен работать в `demo`, используйте ключи Binance Spot Testnet. Для production лучше хранить отдельные secrets в GitHub Environment и запускать workflow только после явного выбора окружения.

## Локальные проверки

```bash
python -m unittest discover -s tests -v
python -m compileall main.py src tests
```

## Ограничения текущей версии

- Поддерживается только `TIMEFRAME=15m`.
- Логика рассчитана на Spot Binance.
- Для реальной торговли нужен внешний процесс-хостинг, GitHub Actions годится только для CI и одноразовых прогонов.