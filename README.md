# Binance Spot Trading Bot

[![CI](https://github.com/kingofgeorgia/tradingbot/actions/workflows/ci.yml/badge.svg)](https://github.com/kingofgeorgia/tradingbot/actions/workflows/ci.yml)
[![Run Bot Once](https://github.com/kingofgeorgia/tradingbot/actions/workflows/run-bot.yml/badge.svg)](https://github.com/kingofgeorgia/tradingbot/actions/workflows/run-bot.yml)

Локальный торговый бот для Binance Spot на Python 3.11+ с EMA crossover стратегией, риск-менеджментом, журналированием и Telegram-уведомлениями.

## Что умеет

- `APP_MODE=demo` для Binance Spot Testnet и `APP_MODE=live` для production.
- Торговля по списку инструментов из `SYMBOLS`, по умолчанию `BTCUSDT,ETHUSDT`.
- Таймфрейм `15m` и стратегия на пересечении `EMA(20)` и `EMA(50)`.
- Локальный `stop-loss` и `take-profit`.
- Безопасный startup reconciliation перед торговым циклом: восстановление recoverable-позиций и блокировка mismatch-сценариев.
- Operator workflow для `inspect`, `acknowledge`, `repair` и `unblock` по проблемным символам.
- Версионированный `state.json` с `schema_version` и backward-compatible migration path для локального runtime state.
- Автоматический recovery path для битого или несовместимого `state.json`: backup исходного файла, reset в пустой local state и operator notification.
- Более подробный `inspect` output с per-symbol runtime status categories, effective runtime mode и operator-context по каждому symbol.
- Настраиваемые heartbeat/summary notifications по runtime health и blocked symbols.
- Cooldown policy для повторяющихся startup/runtime alerts, чтобы persistent проблемы не спамили operator channel каждый цикл.
- `inspect --json` для машиночитаемого runtime status с устойчивым набором top-level keys и per-symbol status payload.
- Отдельный regression test на стабильность JSON-ключей для `inspect --json`, чтобы machine-readable contract не дрейфовал незаметно.
- End-to-end subprocess smoke для `RUNTIME_MODE=startup-check-only`, чтобы bootstrap path проверялся не только unit-тестами.
- End-to-end subprocess smoke для `RUNTIME_MODE=observe-only`, чтобы runtime loop подтверждал отсутствие execution при сохранении signal processing.
- End-to-end subprocess smoke для `RUNTIME_MODE=no-new-entries`, чтобы BUY signals логировались, но новые позиции не открывались.
- `repair` и `unblock` поддерживают `--dry-run`, чтобы оператор мог проверить manual action без backup/state mutation и journal writes.
- В `docs/architecture/operator-playbook.md` есть точный manual testnet checklist для blocked-сценариев NEXT-15..17.
- Для Windows есть готовый PowerShell runbook в `docs/architecture/operator-testnet-powershell-runbook.md` и шаблон отчета в `docs/architecture/testnet-evidence-report-template.md`.
- Для быстрого ручного прогона по `BTCUSDT` есть one-page runbook в `docs/architecture/operator-testnet-quick-runbook.md` и предзаполненный draft report в `docs/architecture/testnet-evidence-report-btcusdt-draft.md`.
- Для самого короткого запуска есть minimal snippet в `docs/architecture/operator-testnet-one-shot-snippet.md`, а для сценариев `NEXT-15` и `NEXT-16` есть отдельные BTCUSDT report drafts.
- Для `NEXT-15` есть отдельный fixed PowerShell block без переменных сценария в `docs/architecture/operator-testnet-next15-btcusdt-snippet.md`.
- Per-symbol overrides для runtime policy и risk sizing поверх общего `.env`-профиля.
- Exchange port поверх Binance adapter для более чистых service/use-case boundaries и test doubles.
- Явная runtime error policy: warning/runtime-io ошибки журналируются без operator alert, а execution/fatal ошибки получают реакцию и уведомление.
- Отдельное startup summary notification после reconciliation, чтобы оператор сразу видел общий стартовый статус runtime.
- Ограничения риска: лимит риска на сделку, размер позиции, число одновременно открытых позиций, дневной лимит убытка и блокировка после серии убытков.
- Логи в консоль и файлы, CSV-журналы сигналов, сделок, ошибок, reconciliation и repair-history.
- Telegram-уведомления о старте, сделках, API-ошибках, startup mismatch и recovery-сценариях.

## Архитектура

- `main.py` — корневая точка входа, добавляет `src` в `PYTHONPATH` и вызывает пакетный entrypoint.
- `src/binance_bot/main.py` — тонкий bootstrap, который собирает runtime и запускает loop.
- `src/binance_bot/services/runtime.py` — composition root, жизненный цикл приложения и startup recovery для невалидного `state.json`.
- `src/binance_bot/services/reconciliation.py` — startup/restart reconciliation и safety guard перед loop.
- `src/binance_bot/services/repair.py` — manual repair flow для blocked symbols и startup issues.
- `src/binance_bot/services/status.py` — runtime status summary, per-symbol runtime categories и formatters для operator flow/observability.
- `src/binance_bot/services/cycle.py` — orchestration одного торгового цикла.
- `src/binance_bot/services/position_monitor.py` — исполнение решений по открытым позициям.
- `src/binance_bot/services/error_handler.py` — единая запись и уведомление по API-ошибкам.
- `src/binance_bot/config.py` — загрузка `.env`, валидация настроек и подготовка runtime-директорий.
- `src/binance_bot/clients/binance_client.py` — REST-клиент Binance Spot.
- `src/binance_bot/core/exchange.py` — exchange error и protocol-based port contracts между runtime/use-cases и конкретным Binance adapter.
- `src/binance_bot/strategy/ema_cross.py` — вычисление EMA и генерация сигналов.
- `src/binance_bot/risk/manager.py` — риск-менеджмент и лимиты торговли.
- `src/binance_bot/orders/manager.py` — открытие и закрытие позиций.
- `src/binance_bot/notify/telegram.py` — уведомления в Telegram.
- `src/binance_bot/use_cases/` — application use-cases для открытия и закрытия позиций.
- `src/binance_bot/core/` — модели, state store, логирование, CSV-журналы, pure decisions и helpers округления.
- `data/state.json` — versioned persistent state payload с `schema_version`, migration boundary и auto-recovery через backup при битом/несовместимом содержимом.
- `docs/architecture/` — архитектурные инварианты и overview проекта.
- `docs/architecture/changelog.md` — хронология архитектурных фаз и ключевых изменений по этапам.
- `docs/project-purpose.md` — подробное описание того, в чем главная суть проекта.
- `docs/manual-reference.md` — индекс полного технического manual по проекту.
- `docs/backlog.md` — рабочий backlog проекта с приоритетами `Now / Next / Later / Not now`.
- `tests/` — unit- и service-level тесты для strategy, risk, order manager, state store, decisions, reconciliation, cycle и position monitor.
- `tests/fixtures/` — sample state payloads для regression-проверок старых и blocked state scenarios.
- `.github/workflows/` — CI и одноразовый запуск бота через GitHub Actions.

## Границы ответственности

- `strategy/` — только генерация сигналов, без сетевых вызовов и без исполнения ордеров.
- `risk/` — только правила риска и sizing.
- `orders/` — только исполнение открытия и закрытия позиций.
- `use_cases/` — application flow для trade execution с явными входами и результатами.
- `core/decisions.py` — pure decision logic без API, notifier, state persistence и journal writes.
- `services/reconciliation.py` — единственная точка startup recovery и mismatch handling.
- `services/` — orchestration и execution flow, но не источник торговых решений.
- `clients/`, `notify/`, CSV-журналы — только IO.

## Operator команды

Просмотр текущего состояния:

```bash
python main.py inspect
```

Машиночитаемый статус:

```bash
python main.py inspect --json
```

Подтверждение startup issue:

```bash
python main.py acknowledge BTCUSDT
```

Ручной repair:

```bash
python main.py repair BTCUSDT restore-from-exchange
python main.py repair BTCUSDT drop-local-state
python main.py repair BTCUSDT restore-from-exchange --dry-run
```

Снятие block после исправления:

```bash
python main.py unblock BTCUSDT
python main.py unblock BTCUSDT --dry-run
```

## Runtime modes

- `RUNTIME_MODE=trade` — normal execution.
- `RUNTIME_MODE=startup-check-only` — только reconciliation без запуска цикла.
- `RUNTIME_MODE=observe-only` — без исполнения BUY/SELL и без auto-close через monitor.
- `RUNTIME_MODE=no-new-entries` — без новых BUY, но с обычной обработкой остального runtime.

Для отдельных символов можно задать более строгий effective runtime mode через `SYMBOL_POLICY_OVERRIDES`. Per-symbol override не ослабляет глобальный `RUNTIME_MODE`, а только делает его строже для конкретного symbol.

## Быстрый старт

1. Установите Python 3.11+.
2. Создайте и активируйте виртуальное окружение.
3. Установите зависимости.
4. Создайте `.env` в корне проекта.
5. Запустите бота или тесты.

### Создание окружения

```bash
python -m venv .venv
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source .venv/Scripts/activate
```

### Установка зависимостей

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest ruff
```

## Настройки

Минимально required в `.env`:

```env
APP_MODE=demo
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=15m
RUN_ONCE=false
```

Дополнительно поддерживаются:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FAST_EMA_PERIOD`
- `SLOW_EMA_PERIOD`
- `STOP_LOSS_PCT`
- `TAKE_PROFIT_PCT`
- `RISK_PER_TRADE_PCT`
- `MAX_POSITION_PCT`
- `MAX_OPEN_POSITIONS_TOTAL`
- `MAX_OPEN_POSITIONS_PER_SYMBOL`
- `DAILY_LOSS_LIMIT_PCT`
- `MAX_CONSECUTIVE_LOSSES`
- `LOOP_INTERVAL_SECONDS`
- `HEARTBEAT_INTERVAL_CYCLES`
- `ALERT_COOLDOWN_SECONDS`
- `ORDER_CONFIRM_TIMEOUT_SECONDS`
- `REQUEST_TIMEOUT_SECONDS`
- `STALE_DATA_MULTIPLIER`
- `QUOTE_ASSET`
- `RUNTIME_MODE`
- `SYMBOL_POLICY_OVERRIDES`

Пример `SYMBOL_POLICY_OVERRIDES`:

```env
SYMBOL_POLICY_OVERRIDES={"BTCUSDT":{"runtime_mode":"observe-only","risk_per_trade_pct":0.02,"max_position_pct":0.05},"ETHUSDT":{"runtime_mode":"no-new-entries"}}
```

Поддерживаемые per-symbol поля:

- `runtime_mode`: `trade`, `observe-only`, `no-new-entries`
- `risk_per_trade_pct`: число `> 0` и `<= 1`
- `max_position_pct`: число `> 0` и `<= 1`

## Запуск

Локальный запуск:

```bash
python main.py
```

Одноразовый локальный прогон:

```bash
set RUN_ONCE=true
python main.py
```

## Проверки

Запуск тестов:

```bash
python -m pytest -q
```

Запуск линтера:

```bash
python -m ruff check .
```

CI в GitHub Actions использует Python 3.11, отдельно гоняет core tests, service-layer smoke, CLI/runtime smoke для startup/runtime modes, regression-проверки sample state fixtures и стабильность `inspect --json` payload.

### Post-smoke checklist

После runtime smoke или `RUN_ONCE=true` прогона быстро проверьте:

- `logs/app.log`: есть startup summary и строка с нужным `runtime_mode`.
- `logs/errors.log`: нет новых execution/fatal ошибок для текущего запуска.
- `data/reconciliation.csv`: есть запись reconciliation со статусом `clean` или ожидаемым issue status.
- `data/errors.csv`: пусто либо содержит только ожидаемые warning/runtime-io записи.
- `data/signals.csv`: для `observe-only` и `no-new-entries` сигнал должен логироваться, даже если execution не произошло.
- `data/trades.csv`: для `observe-only` и `no-new-entries` не должно появляться неожиданных BUY/SELL записей.
- `data/repair.csv`: после smoke без manual actions не должно появляться новых repair/unblock записей.

## GitHub Actions

- `CI` — ставит зависимости, запускает `ruff check .`, core tests, service-layer smoke и state regression smoke.
- `Run Bot Once` — запускает бота вручную через `workflow_dispatch` c `APP_MODE`, `SYMBOLS` и GitHub Secrets.

## Текущее покрытие тестами

- `tests/test_ema_cross.py`
- `tests/test_risk_manager.py`
- `tests/test_order_manager.py`
- `tests/test_state_store.py`
- `tests/test_decisions.py`
- `tests/test_reconciliation.py`
- `tests/test_repair.py`
- `tests/test_status.py`
- `tests/test_state_fixtures.py`
- `tests/test_position_monitor.py`
- `tests/test_cycle.py`

Общие test doubles находятся в `tests/fakes.py`.