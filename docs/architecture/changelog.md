# Architecture Changelog

Краткая история архитектурных фаз проекта. Этот файл фиксирует, что именно менялось по фазам и какие модули стали ключевыми результатами каждого этапа.

## Phase 1

- Собран базовый runtime для Binance Spot с bootstrap entrypoint, settings, REST client, strategy, risk manager, order execution, state store и journaling.
- Добавлены базовые runtime adapters для logging и Telegram notifications.
- Подняты README, CI workflows и первые unit tests для strategy и risk.

Ключевые модули:
- [main.py](../main.py)
- [src/binance_bot/main.py](../src/binance_bot/main.py)
- [src/binance_bot/config.py](../src/binance_bot/config.py)
- [src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py)
- [src/binance_bot/strategy/ema_cross.py](../src/binance_bot/strategy/ema_cross.py)
- [src/binance_bot/risk/manager.py](../src/binance_bot/risk/manager.py)
- [src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py)
- [src/binance_bot/core/models.py](../src/binance_bot/core/models.py)
- [src/binance_bot/core/state.py](../src/binance_bot/core/state.py)
- [src/binance_bot/core/journal.py](../src/binance_bot/core/journal.py)
- [src/binance_bot/core/logging_setup.py](../src/binance_bot/core/logging_setup.py)
- [src/binance_bot/notify/telegram.py](../src/binance_bot/notify/telegram.py)
- [README.md](../README.md)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- [.github/workflows/run-bot.yml](../.github/workflows/run-bot.yml)

## Phase 2

- Runtime loop перенесен в composition-root service, а bootstrap стал тоньше.
- Усилена тестовая база вокруг state store и order manager.
- Тестовая структура и CI-поток приведены к более стабильному виду для последующих рефакторингов.

Ключевые модули:
- [src/binance_bot/main.py](../src/binance_bot/main.py)
- [src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py)
- [tests/test_order_manager.py](../tests/test_order_manager.py)
- [tests/test_state_store.py](../tests/test_state_store.py)
- [tests/fakes.py](../tests/fakes.py)
- [pyproject.toml](../pyproject.toml)

## Phase 3

- Добавлены архитектурные инварианты и project overview как опора для дальнейших изменений.
- Выделен pure decision layer, а orchestration в cycle и position monitor стал тоньше.
- Расширены service-level tests для orchestration и decision logic.
- Исправлено округление quantity по step size через общий helper.
- Починен импорт тестов в CI и обновлена документация под новую структуру.

Ключевые модули:
- [docs/architecture/system-overview.md](./system-overview.md)
- [docs/architecture/invariants.md](./invariants.md)
- [AI_RULES.md](../AI_RULES.md)
- [src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py)
- [src/binance_bot/core/rounding.py](../src/binance_bot/core/rounding.py)
- [src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py)
- [src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py)
- [tests/test_decisions.py](../tests/test_decisions.py)
- [tests/test_cycle.py](../tests/test_cycle.py)
- [tests/test_position_monitor.py](../tests/test_position_monitor.py)
- [tests/__init__.py](../tests/__init__.py)

## Phase 4

- Выделен application layer для trade execution через use-cases и порты.
- `orders/manager.py` стал тонкой facade над execution use-cases.

Ключевые модули:
- [src/binance_bot/core/trade_execution.py](../src/binance_bot/core/trade_execution.py)
- [src/binance_bot/use_cases/ports.py](../src/binance_bot/use_cases/ports.py)
- [src/binance_bot/use_cases/trade_execution.py](../src/binance_bot/use_cases/trade_execution.py)
- [src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py)
- [tests/test_trade_execution.py](../tests/test_trade_execution.py)

## Phase 4.1

- В state contract добавлены reconciliation-aware поля для blocked symbols, suspect positions и startup issues.
- Появились exchange snapshot/recovery APIs и отдельный reconciliation service.
- Safety guardrails встроены в runtime, cycle, risk manager и position monitor.
- Reconciliation сценарии покрыты тестами и отражены в архитектурной документации.

Ключевые модули:
- [src/binance_bot/core/models.py](../src/binance_bot/core/models.py)
- [src/binance_bot/core/state.py](../src/binance_bot/core/state.py)
- [src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py)
- [src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py)
- [src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py)
- [src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py)
- [src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py)
- [src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py)
- [src/binance_bot/risk/manager.py](../src/binance_bot/risk/manager.py)
- [tests/test_reconciliation.py](../tests/test_reconciliation.py)

## Phase 4.2

- Добавлен operator workflow для inspect, acknowledge, repair и unblock.
- Появился status service для operator reporting и runtime inspect flow.
- Добавлены repair journal, acknowledgement tracking, alert dedupe и operator playbook.

Ключевые модули:
- [src/binance_bot/main.py](../src/binance_bot/main.py)
- [src/binance_bot/services/repair.py](../src/binance_bot/services/repair.py)
- [src/binance_bot/services/status.py](../src/binance_bot/services/status.py)
- [src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py)
- [docs/architecture/operator-playbook.md](./operator-playbook.md)
- [tests/test_repair.py](../tests/test_repair.py)
- [tests/test_status.py](../tests/test_status.py)

## Phase 5

- Добавлены safe runtime modes и runtime summaries для более безопасной эксплуатации.
- Runtime errors получили явную классификацию и единый handling path.
- Добавлены regression fixtures и усилены CI/documentation для state и service smoke сценариев.

Ключевые модули:
- [src/binance_bot/config.py](../src/binance_bot/config.py)
- [src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py)
- [src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py)
- [src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py)
- [src/binance_bot/core/errors.py](../src/binance_bot/core/errors.py)
- [src/binance_bot/services/error_handler.py](../src/binance_bot/services/error_handler.py)
- [tests/fixtures/legacy_state.json](../tests/fixtures/legacy_state.json)
- [tests/fixtures/blocked_state.json](../tests/fixtures/blocked_state.json)
- [tests/test_state_fixtures.py](../tests/test_state_fixtures.py)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml)

## Cross-phase

- Добавлен встроенный backlog проекта как рабочий planning artifact для следующих итераций.

Ключевые модули:
- [docs/backlog.md](../backlog.md)