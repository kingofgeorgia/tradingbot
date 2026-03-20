# Tradingbot Manual Reference

Полный единый manual проекта в компактном формате.

One-line summary: [docs/project-purpose.md](./project-purpose.md) — зачем проект существует, что в нем главное и почему здесь приоритет у safety/operator контура, а не у усложнения стратегии.

## Содержание

- [Быстрые переходы](#быстрые-переходы)
- [Как читать проект](#как-читать-проект)
- [Root Files](#root-files)
- [Documentation Files](#documentation-files)
- [Modules](#modules)
- [Operator Flow](#operator-flow)
- [Tests](#tests)
- [Fixture Files](#fixture-files)
- [Краткая навигация](#краткая-навигация)

## Быстрые переходы

- [К модулю](#modules)
- [К operator flow](#operator-flow)
- [К тестам](#tests)
- [К содержанию](#содержание)

## Как читать проект

Рекомендуемый порядок:
1. [README.md](../README.md)
2. [docs/architecture/system-overview.md](./architecture/system-overview.md)
3. [docs/architecture/invariants.md](./architecture/invariants.md)
4. [src/binance_bot/main.py](../src/binance_bot/main.py)
5. [src/binance_bot/config.py](../src/binance_bot/config.py)
6. [src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py)
7. [src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py)
8. [src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py)
9. [src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py)
10. [tests/test_reconciliation.py](../tests/test_reconciliation.py)

## Root Files

- [main.py](../main.py) — корневой entrypoint; добавляет `src` в import path и передает управление пакетному entrypoint.
- [README.md](../README.md) — основной вход в проект; quick start, архитектура, operator commands, runtime modes.
- [AI_RULES.md](../AI_RULES.md) — архитектурные и operational guardrails.
- [pyproject.toml](../pyproject.toml) — конфигурация Ruff и target-version Python.
- [requirements.txt](../requirements.txt) — Python-зависимости проекта.

Навигация: [к модулю](#modules) | [к operator flow](#operator-flow) | [к тестам](#tests) | [к содержанию](#содержание)

## Documentation Files

- [docs/backlog.md](./backlog.md) — рабочий backlog проекта.
- [docs/project-purpose.md](./project-purpose.md) — подробное описание главной сути проекта и его engineering priority.
- [docs/architecture/changelog.md](./architecture/changelog.md) — хронология архитектурных фаз и изменений.
- [docs/architecture/system-overview.md](./architecture/system-overview.md) — high-level карта модулей проекта.
- [docs/architecture/invariants.md](./architecture/invariants.md) — архитектурные инварианты проекта.
- [docs/architecture/operator-playbook.md](./architecture/operator-playbook.md) — операционный playbook для repair flow.
- [docs/architecture/operator-playbook.md](./architecture/operator-playbook.md) также содержит точный manual testnet checklist для blocked-сценариев `NEXT-15`, `NEXT-16`, `NEXT-17`.
- [docs/architecture/operator-testnet-powershell-runbook.md](./architecture/operator-testnet-powershell-runbook.md) — готовый Windows PowerShell runbook для сбора evidence по `NEXT-15`, `NEXT-16`, `NEXT-17`.
- [docs/architecture/testnet-evidence-report-template.md](./architecture/testnet-evidence-report-template.md) — шаблон отчета для фиксации результатов ручного testnet-прогона.
- [docs/architecture/operator-testnet-quick-runbook.md](./architecture/operator-testnet-quick-runbook.md) — one-page quick runbook для `BTCUSDT` по сценариям `NEXT-15` и `NEXT-16`.
- [docs/architecture/testnet-evidence-report-btcusdt-draft.md](./architecture/testnet-evidence-report-btcusdt-draft.md) — предзаполненный draft report для ручного testnet-прогона по `BTCUSDT`.
- [docs/architecture/operator-testnet-one-shot-snippet.md](./architecture/operator-testnet-one-shot-snippet.md) — минимальный PowerShell snippet для одного evidence run без полного runbook.
- [docs/architecture/testnet-evidence-report-btcusdt-next15.md](./architecture/testnet-evidence-report-btcusdt-next15.md) — сценарный отчет-заготовка для `NEXT-15`.
- [docs/architecture/testnet-evidence-report-btcusdt-next16.md](./architecture/testnet-evidence-report-btcusdt-next16.md) — сценарный отчет-заготовка для `NEXT-16`.

Навигация: [к модулю](#modules) | [к operator flow](#operator-flow) | [к тестам](#tests) | [к содержанию](#содержание)

## Modules

### Package Root

- [src/binance_bot/__init__.py](../src/binance_bot/__init__.py) — marker file пакета `binance_bot`.
- [src/binance_bot/main.py](../src/binance_bot/main.py) — пакетный entrypoint; строит runtime, маршрутизирует operator commands, запускает reconciliation и trading loop. Ключевые функции: `run(...)`, `_run_operator_command(...)`.

### Config Layer

- [src/binance_bot/config.py](../src/binance_bot/config.py) — загрузка `.env`, валидация настроек, пути к state/journals/logs/backups, heartbeat cadence и per-symbol policy overrides. Ключевые сущности: `AppMode`, `RuntimeMode`, `SymbolPolicyOverride`, `Settings`, `load_settings()`, `ensure_runtime_directories(...)`.

### Client Layer

- [src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py) — Binance Spot REST adapter и exchange snapshots для reconciliation. Ключевые сущности: `BinanceAPIError`, `BinanceSpotClient`. Основные методы: `sync_time()`, `get_account()`, `get_klines()`, `get_latest_price()`, `get_symbol_filters()`, `create_market_order()`, `get_order()`, `get_open_orders()`, `get_my_trades()`, `get_position_snapshot()`, `confirm_order_filled()`, `calculate_average_fill_price()`, `calculate_quote_fee()`, `round_step_size()`.

### Core Layer

- [src/binance_bot/core/exchange.py](../src/binance_bot/core/exchange.py) — exchange error и protocol-based port contracts для runtime/services/use-cases. Ключевые сущности: `ExchangeAPIError`, `ExchangeExecutionPort`, `ExchangeMarketDataPort`, `ExchangeReconciliationPort`, `ExchangeRuntimePort`.
- [src/binance_bot/core/models.py](../src/binance_bot/core/models.py) — domain models и persistent runtime state, включая `schema_version` в `BotState` и per-symbol runtime categories в `RuntimeStatusReport`. Ключевые классы: `Candle`, `SymbolFilters`, `Position`, `ExchangePositionSnapshot`, `StartupIssue`, `SymbolRuntimeStatus`, `ReconciliationResult`, `RepairRecord`, `RuntimeStatusReport`, `BotState`.
- [src/binance_bot/core/state.py](../src/binance_bot/core/state.py) — JSON persistence layer с migration boundary по `schema_version` и recovery backup path для битого/несовместимого state payload. Ключевые сущности: `StateLoadError`, `StateStore`, `load()`, `recover(...)`, `save(state)`, `migrate_state_payload(...)`.
- [src/binance_bot/core/journal.py](../src/binance_bot/core/journal.py) — append-only CSV journaling. Ключевые сущности: `CsvJournal`, `write(row)`.
- [src/binance_bot/core/logging_setup.py](../src/binance_bot/core/logging_setup.py) — настройка логгеров. Ключевые сущности: `Loggers`, `configure_logging(...)`.
- [src/binance_bot/core/errors.py](../src/binance_bot/core/errors.py) — классификация runtime errors с policy reaction и notification routing. Ключевые сущности: `ErrorDescriptor`, `classify_runtime_error(...)`.
- [src/binance_bot/services/alerts.py](../src/binance_bot/services/alerts.py) — cooldown policy для repeated startup/runtime alerts. Ключевые сущности: `send_alert_with_cooldown(...)`, `should_send_alert(...)`.
- [src/binance_bot/core/rounding.py](../src/binance_bot/core/rounding.py) — единая step-size rounding logic. Ключевая функция: `round_down_to_step(...)`.
- [src/binance_bot/core/trade_execution.py](../src/binance_bot/core/trade_execution.py) — pure result models для BUY/SELL execution. Ключевые сущности: `OpenPositionResult`, `ClosePositionResult`, `build_open_position_result(...)`, `calculate_close_result(...)`.
- [src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py) — pure decision layer. Ключевые сущности: `RiskDecision`, `CloseDecision`, `SignalDecision`, `ReconciliationDecision`, `SymbolBlockDecision`, `StateRepairDecision`, `ManualRepairDecision`, `IssueAcknowledgementDecision`, `decide_risk_entry(...)`, `decide_position_close(...)`, `decide_signal_action(...)`, `decide_state_repair(...)`, `decide_reconciliation_action(...)`, `decide_symbol_block(...)`, `decide_manual_repair_action(...)`, `decide_unblock_allowed(...)`, `decide_issue_acknowledgement(...)`.

### Strategy Layer

- [src/binance_bot/strategy/ema_cross.py](../src/binance_bot/strategy/ema_cross.py) — генерация сигналов на EMA crossover без side effects. Ключевые сущности: `TradeSignal`, `EmaCrossStrategy`, `evaluate(...)`.

### Risk Layer

- [src/binance_bot/risk/manager.py](../src/binance_bot/risk/manager.py) — risk rules, sizing, daily halt logic и применение per-symbol sizing overrides. Ключевые сущности: `RiskManager`, `refresh_trading_day(...)`, `can_open_position(...)`, `calculate_order_quantity(...)`, `register_closed_trade(...)`.

### Orders Layer

- [src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py) — thin facade вокруг execution use-cases и reconciliation mutations. Ключевые сущности: `OrderManager`, `log_signal(...)`, `open_long(...)`, `close_position(...)`, `restore_position_from_exchange(...)`, `drop_local_position(...)`, `mark_position_unrecoverable(...)`.

### Use Cases Layer

- [src/binance_bot/use_cases/ports.py](../src/binance_bot/use_cases/ports.py) — dependency protocols для execution use-cases поверх exchange port contracts. Ключевые сущности: `TradeExecutionClient`, `TradeRiskManager`, `TradeStateStore`, `TradeJournal`, `TradeNotifier`, `TradeLogger`.
- [src/binance_bot/use_cases/trade_execution.py](../src/binance_bot/use_cases/trade_execution.py) — application-level BUY/SELL flows. Ключевые сущности: `OpenPositionUseCase`, `ClosePositionUseCase`, `_confirm_order(...)`, `_utc_now_iso()`.

### Notify Layer

- [src/binance_bot/notify/telegram.py](../src/binance_bot/notify/telegram.py) — Telegram adapter для runtime notifications. Ключевые сущности: `TelegramNotifier`, `enabled`, `send(message)`.

### Service Layer

- [src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py) — composition root, lifecycle loop, runtime heartbeat notifications и startup recovery для невалидного `state.json`; concrete Binance client подключается здесь как реализация exchange port. Ключевые сущности: `AppRuntime`, `ensure_runtime_state_file(...)`, `build_runtime()`, `reconcile_startup(...)`, `run_loop(...)`.
- [src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py) — orchestration одного торгового цикла с effective per-symbol runtime policy для BUY/SELL execution. Ключевые сущности: `process_cycle(...)`, `_load_portfolio_snapshot(...)`, `_handle_sell_signal(...)`, `_handle_buy_signal(...)`, `_notify_halt_reason(...)`.
- [src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py) — управление уже открытыми позициями с учетом per-symbol `observe-only` override. Ключевая сущность: `manage_open_positions(...)`.
- [src/binance_bot/services/error_handler.py](../src/binance_bot/services/error_handler.py) — единая запись runtime/API ошибок с учетом `reaction` и `notify_operator`. Ключевые сущности: `utc_now_iso()`, `record_api_error(...)`.

Навигация: [к operator flow](#operator-flow) | [к тестам](#tests) | [к содержанию](#содержание)

## Operator Flow

Команды оператора:
- `python main.py inspect`
- `python main.py inspect --json`
- `python main.py acknowledge BTCUSDT`
- `python main.py repair BTCUSDT restore-from-exchange`
- `python main.py repair BTCUSDT drop-local-state`
- `python main.py repair BTCUSDT restore-from-exchange --dry-run`
- `python main.py unblock BTCUSDT`
- `python main.py unblock BTCUSDT --dry-run`

- [src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py) — startup reconciliation и блокировка mismatch scenarios. Ключевые сущности: `load_exchange_snapshot(...)`, `reconcile_symbol_state(...)`, `reconcile_runtime_state(...)`, `apply_reconciliation_result(...)`.
- [src/binance_bot/services/repair.py](../src/binance_bot/services/repair.py) — manual repair и unblock flow, включая text/json paths для `inspect`. Ключевые сущности: `inspect_runtime_issues(...)`, `acknowledge_issue(...)`, `repair_symbol_state(...)`, `unblock_symbol(...)`, `_backup_state_before_manual_action(...)`.
- [src/binance_bot/services/status.py](../src/binance_bot/services/status.py) — status summary для `inspect`, per-symbol runtime categories, JSON serializer и heartbeat notifications. Ключевые сущности: `build_runtime_status_report(...)`, `format_status_report(...)`, `format_status_report_json(...)`, `runtime_status_report_to_dict(...)`, `format_runtime_health_notification(...)`, `format_startup_summary_notification(...)`.
- [docs/architecture/operator-playbook.md](./architecture/operator-playbook.md) — playbook для ручной работы с проблемными символами.
- В `operator-playbook` теперь зафиксирован пошаговый manual testnet checklist для сценариев `local-position-missing-on-exchange`, `exchange-position-without-local-state` и длительной ревизии CSV/log artifacts.
- [docs/architecture/operator-testnet-powershell-runbook.md](./architecture/operator-testnet-powershell-runbook.md) — готовые PowerShell команды для snapshot, startup-check-only run, checkpoint metrics и archive.
- [docs/architecture/testnet-evidence-report-template.md](./architecture/testnet-evidence-report-template.md) — шаблон для итоговой записи evidence и operator conclusions.
- [docs/architecture/operator-testnet-quick-runbook.md](./architecture/operator-testnet-quick-runbook.md) — сокращенный runbook без общего scaffolding для быстрого прогона `NEXT-15` и `NEXT-16`.
- [docs/architecture/testnet-evidence-report-btcusdt-draft.md](./architecture/testnet-evidence-report-btcusdt-draft.md) — готовая заготовка отчета с полями под `BTCUSDT`.
- [docs/architecture/operator-testnet-one-shot-snippet.md](./architecture/operator-testnet-one-shot-snippet.md) — минимальный snippet для быстрого baseline + `startup-check-only` run.
- [docs/architecture/testnet-evidence-report-btcusdt-next15.md](./architecture/testnet-evidence-report-btcusdt-next15.md) и [docs/architecture/testnet-evidence-report-btcusdt-next16.md](./architecture/testnet-evidence-report-btcusdt-next16.md) — отдельные сценарные формы отчета вместо одного общего черновика.

Порядок работы:
1. Запустить `inspect` и определить problem symbols.
2. При необходимости подтвердить issue через `acknowledge`.
3. Выполнить `repair` с разрешенным действием.
4. После выравнивания state выполнить `unblock`.
5. Повторно проверить статус через `inspect`.

Post-smoke checklist:
1. Проверить [logs/app.log](../logs/app.log): есть startup summary и запись о runtime mode или `RUN_ONCE enabled`.
2. Проверить [logs/errors.log](../logs/errors.log): нет новых execution/fatal ошибок для текущего smoke-прогона.
3. Проверить [data/reconciliation.csv](../data/reconciliation.csv): есть строка reconciliation с ожидаемым `status`.
4. Проверить [data/errors.csv](../data/errors.csv): отсутствуют неожиданные runtime/API ошибки.
5. Проверить [data/signals.csv](../data/signals.csv): signal logging присутствует для сценариев `observe-only` и `no-new-entries`.
6. Проверить [data/trades.csv](../data/trades.csv): нет execution rows, если smoke должен был только проверить suppression execution.
7. Проверить [data/repair.csv](../data/repair.csv): нет новых manual repair/unblock записей, если оператор не запускал repair flow.

Policy note:
- `SYMBOL_POLICY_OVERRIDES` принимает JSON-объект по символам, например `{"BTCUSDT":{"runtime_mode":"observe-only","risk_per_trade_pct":0.02,"max_position_pct":0.05}}`.
- Per-symbol `runtime_mode` не может ослабить глобальный `RUNTIME_MODE`; effective mode для символа всегда выбирается как более строгий из двух.
- `inspect` теперь показывает по каждому symbol его runtime category (`ready`, `position-open`, `suspect`, `blocked`), effective mode, issue/acknowledgement status и last manual action.
- `ALERT_COOLDOWN_SECONDS` задает suppression window для повторяющихся startup/runtime alerts с одинаковым alert key; `0` отключает cooldown.
- `inspect --json` возвращает стабильный top-level payload: `runtime_mode`, `open_positions`, `blocked_symbols`, `suspect_positions`, `startup_issue_keys`, `symbol_statuses`, `last_reconciled_at`, `last_reconciliation_status`, `last_manual_review_at`.
- `repair ... --dry-run` и `unblock ... --dry-run` проходят тот же decision/reconciliation path, но не делают backup, не сохраняют state и не пишут repair journal.
- `startup-check-only` smoke теперь прогоняется как subprocess path: reconciliation выполняется, startup summary отправляется, trading loop не стартует.
- `observe-only` smoke теперь прогоняется как subprocess path с `RUN_ONCE`: reconciliation и один runtime cycle выполняются, signal logging остается активным, но execution не происходит.
- `no-new-entries` smoke теперь прогоняется как subprocess path с `RUN_ONCE`: reconciliation и один runtime cycle выполняются, BUY signals логируются, но новые позиции не открываются.

Навигация: [к модулю](#modules) | [к тестам](#tests) | [к содержанию](#содержание)

## Tests

### Test Infrastructure

- [tests/__init__.py](../tests/__init__.py) — marker file test package для корректных imports в CI.
- [tests/fakes.py](../tests/fakes.py) — central test doubles. Ключевые сущности: `FakeJournal`, `FakeCsvJournal`, `FakeNotifier`, `FakeLogger`, `FakeLoggers`, `FakeStateStore`, `FakeRiskManager`, `FakeBinanceClient`, `make_settings()`.

### Strategy Tests

- [tests/test_ema_cross.py](../tests/test_ema_cross.py) — тесты EMA crossover. Ключевые сущности: `build_candles(...)`, `EmaCrossStrategyTests`.

### Risk Tests

- [tests/test_risk_manager.py](../tests/test_risk_manager.py) — тесты risk rules и sizing. Ключевые сущности: `make_settings()`, `RiskManagerTests`.

### Orders And State Tests

- [tests/test_order_manager.py](../tests/test_order_manager.py) — тесты thin order facade и reconciliation mutations. Ключевая сущность: `OrderManagerTests`.
- [tests/test_state_store.py](../tests/test_state_store.py) — тесты JSON state persistence. Ключевая сущность: `StateStoreTests`.

### Decision And Service Tests

- [tests/test_decisions.py](../tests/test_decisions.py) — тесты pure decision layer. Ключевая сущность: `DecisionTests`.
- [tests/test_cycle.py](../tests/test_cycle.py) — тесты одного торгового цикла. Ключевая сущность: `CycleTests`.
- [tests/test_position_monitor.py](../tests/test_position_monitor.py) — тесты open-position monitoring. Ключевая сущность: `PositionMonitorTests`.
- [tests/test_trade_execution.py](../tests/test_trade_execution.py) — тесты execution result models и BUY/SELL use-cases. Ключевые сущности: `TradeExecutionModelTests`, `OpenPositionUseCaseTests`, `ClosePositionUseCaseTests`.
- [tests/test_reconciliation.py](../tests/test_reconciliation.py) — тесты startup reconciliation и mismatch handling. Ключевые сущности: `FakeOrderManager`, `FakeStrategy`, `ReconciliationTests`.
- [tests/test_repair.py](../tests/test_repair.py) — тесты operator repair flow. Ключевые сущности: `FakeOrderManager`, `RepairFlowTests`.
- [tests/test_cli_smoke.py](../tests/test_cli_smoke.py) — subprocess-level smoke tests для operator commands и runtime mode entrypoints. Ключевая сущность: `CliSmokeTests`.
- [tests/test_status.py](../tests/test_status.py) — тесты operator status report. Ключевая сущность: `StatusTests`.
- [tests/test_status_json_format.py](../tests/test_status_json_format.py) — regression-тест на стабильность top-level и per-symbol JSON keys для `inspect --json`. Ключевая сущность: `StatusJsonFormatTests`.
- [tests/test_state_fixtures.py](../tests/test_state_fixtures.py) — regression fixtures для state compatibility. Ключевая сущность: `StateFixturesTests`.

Навигация: [к модулю](#modules) | [к operator flow](#operator-flow) | [к содержанию](#содержание)

## Fixture Files

- [tests/fixtures/legacy_state.json](../tests/fixtures/legacy_state.json) — sample legacy state без reconciliation fields.
- [tests/fixtures/blocked_state.json](../tests/fixtures/blocked_state.json) — sample blocked state с startup issue, blocked symbol и reconciliation metadata.

## Краткая навигация

- Архитектурная история: [docs/architecture/changelog.md](./architecture/changelog.md)
- Operator flow: [docs/architecture/operator-playbook.md](./architecture/operator-playbook.md)
- Рабочий backlog: [docs/backlog.md](./backlog.md)