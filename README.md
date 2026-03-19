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
- `src/binance_bot/main.py` — тонкий bootstrap и основной цикл.
- `src/binance_bot/services/runtime.py` — сборка runtime-зависимостей.
- `src/binance_bot/services/cycle.py` — orchestration одного торгового цикла.
- `src/binance_bot/services/position_monitor.py` — контроль открытых позиций по локальному stop-loss / take-profit.
- `src/binance_bot/services/error_handler.py` — единая обработка и журналирование API-ошибок.
- `src/binance_bot/config.py` — загрузка `.env`, валидация настроек и подготовка runtime-директорий.
- `src/binance_bot/clients/binance_client.py` — REST-клиент Binance Spot.
- `src/binance_bot/strategy/ema_cross.py` — вычисление EMA и генерация сигналов.
- `src/binance_bot/risk/manager.py` — риск-менеджмент и лимиты торговли.
- `src/binance_bot/orders/manager.py` — открытие и закрытие позиций.
- `src/binance_bot/notify/telegram.py` — уведомления в Telegram.
- `src/binance_bot/core/` — модели, state store, логирование и CSV-журналы.
- `docs/architecture/` — архитектурные инварианты и overview проекта.
- `tests/` — unit-тесты стратегии, risk manager, order manager и state store.
- `.github/workflows/` — CI и одноразовый запуск бота через GitHub Actions.

## Быстрый старт

1. Установите Python 3.11+.
2. Создайте виртуальное окружение.

```bash
python -m venv .venv