# Backlog

Рабочий backlog проекта с приоритетами `Now / Next / Later / Not now`.

## How To Use

- `Now` — задачи, которые стоит брать в ближайшие итерации.
- `Next` — следующий слой после закрытия `Now`.
- `Later` — полезные направления, но без срочности.
- `Not now` — сознательно отложенные темы, чтобы не размывать фокус.
- При переносе задачи вверх лучше сразу добавлять ссылку на PR, issue или короткий owner/контекст.
- Поля у задач:
	- `owner` — кто ведет задачу: `copilot`, `user` или совместно.
	- `status` — `todo`, `in-progress`, `blocked`, `done`, `parked`.
	- `target` — целевая дата пересмотра или завершения; для `done` это дата, на которую задача была закрыта.
	- `files` — ключевые файлы и модули, которыми задача была закрыта.
- История закрытых фаз и архитектурных изменений вынесена в [architecture/changelog.md](./architecture/changelog.md).

## New Ideas Sorted By Impact / Effort

### High Impact / Low Effort

- `NOW-15` Добавить state backup snapshot перед любым manual repair действием.
- `NEXT-06` Добавить startup summary notification после reconciliation.
- `NOW-18` Добавить idempotency tests для повторного startup reconciliation без лишних side effects.
- `NEXT-09` Добавить alert cooldown policy для повторяющихся startup/runtime alerts.

### High Impact / Medium Effort

- `NEXT-19` Добавить dry-run режим для `repair` и `unblock`.
- `NOW-17` Добавить subprocess-level CLI smoke tests для operator commands.
- `NEXT-07` Добавить recovery path для битого или частично несовместимого `state.json`.

### Medium Impact / Medium Effort

- `NEXT-08` Добавить per-symbol runtime status categories и более подробный inspect output.
- `LATER-06` Добавить manual review queue для unresolved startup/runtime issues.

### Medium Impact / Higher Effort

- `LATER-07` Добавить graceful degradation mode при частичной недоступности exchange API.

## Now

- `NOW-15` Добавить state backup snapshot перед любым manual repair действием.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-18` Добавить idempotency tests для повторного startup reconciliation без лишних side effects.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-01` Добавить CLI integration test для `inspect`.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-02` Добавить CLI integration test для `acknowledge <SYMBOL>`.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-03` Добавить CLI integration test для `repair <SYMBOL> restore-from-exchange`.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-04` Добавить CLI integration test для `repair <SYMBOL> drop-local-state`.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-05` Добавить CLI integration test для `unblock <SYMBOL>` с open/closed issue сценариями.
	owner: copilot
	status: done
	target: 2026-03-20
- `NOW-17` Добавить subprocess-level CLI smoke tests для operator commands.
	owner: copilot
	status: done
	target: 2026-03-20

## Next

- `NEXT-01` Ввести `schema_version` в state payload и backward-compatible migration path.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-02` Добавить heartbeat/summary notifications по runtime health и blocked symbols.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-03` Поддержать per-symbol overrides для risk/runtime policy.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-04` Выделить exchange port поверх Binance client для более чистых service/use-case тестов.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-05` Развести runtime error categories по policy реакции и уведомлениям.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-06` Добавить startup summary notification после reconciliation.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-07` Добавить recovery path для битого или частично несовместимого `state.json`.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-08` Добавить per-symbol runtime status categories и более подробный inspect output.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-09` Добавить alert cooldown policy для повторяющихся startup/runtime alerts.
	owner: copilot
	status: done
	target: 2026-03-20
- `NEXT-10` Добавить `inspect --json` для машиночитаемого runtime status.
	owner: copilot
	status: todo
	target: 2026-04-22
- `NEXT-11` Добавить тест на JSON-формат статуса и стабильность ключей ответа.
	owner: copilot
	status: todo
	target: 2026-04-22
- `NEXT-12` Добавить end-to-end smoke test для режима `startup-check-only`.
	owner: copilot
	status: todo
	target: 2026-04-24
- `NEXT-13` Добавить end-to-end smoke test для режима `observe-only`.
	owner: copilot
	status: todo
	target: 2026-04-24
- `NEXT-14` Добавить end-to-end smoke test для режима `no-new-entries`.
	owner: copilot
	status: todo
	target: 2026-04-24
- `NEXT-15` Прогнать testnet-сценарий `local position missing on exchange` и записать фактический результат.
	owner: user
	status: blocked
	target: 2026-04-25
- `NEXT-16` Прогнать testnet-сценарий `exchange position restored into local state` и обновить operator playbook.
	owner: user
	status: blocked
	target: 2026-04-25
- `NEXT-17` Проверить поведение signal/trade/error/reconciliation/repair CSV при длительном runtime и задокументировать policy ротации.
	owner: user
	status: blocked
	target: 2026-04-27
- `NEXT-18` Добавить короткий operational checklist для ревизии логов и журналов после runtime smoke.
	owner: copilot
	status: todo
	target: 2026-04-27
- `NEXT-19` Добавить dry-run режим для `repair` и `unblock`.
	owner: copilot
	status: todo
	target: 2026-04-29

## Later

- `LATER-01` Добавить SQLite/Postgres event store, если CSV-журналов перестанет хватать для аудита и аналитики.
	owner: user
	status: todo
	target: 2026-05-01
- `LATER-02` Сделать отдельный backtesting harness для strategy layer без смешивания с runtime execution кодом.
	owner: copilot
	status: todo
	target: 2026-05-10
- `LATER-03` Вынести operator/status слой в небольшой локальный dashboard или TUI, если CLI станет узким местом.
	owner: user
	status: todo
	target: 2026-05-20
- `LATER-04` Поддержать несколько стратегий через явный strategy registry, если появится второй реальный strategy flow.
	owner: copilot
	status: todo
	target: 2026-06-01
- `LATER-05` Добавить richer analytics по сделкам, recovery incidents и blocked-symbol history.
	owner: user
	status: todo
	target: 2026-06-10
- `LATER-06` Добавить manual review queue для unresolved startup/runtime issues.
	owner: copilot
	status: todo
	target: 2026-06-20
- `LATER-07` Добавить graceful degradation mode при частичной недоступности exchange API.
	owner: copilot
	status: todo
	target: 2026-06-30

## Not now

- `NOT-NOW-01` Автоматический destructive repair без подтверждения оператора.
	owner: user
	status: parked
	target: revisit after operator flow maturity
- `NOT-NOW-02` Multi-exchange execution abstraction до появления реального второго execution target.
	owner: user
	status: parked
	target: revisit after second venue requirement
- `NOT-NOW-03` Полноценный web dashboard как обязательная часть runtime.
	owner: user
	status: parked
	target: revisit after CLI/operator pain becomes real
- `NOT-NOW-04` Ранний переход на БД, очереди или microservice split без явного operational pressure.
	owner: user
	status: parked
	target: revisit after CSV/log limits are observed
- `NOT-NOW-05` Новые стратегии, пока не стабилизирован текущий safety/operator контур.
	owner: user
	status: parked
	target: revisit after current runtime is stable
- `NOT-NOW-06` ML/AI-оптимизация сигналов до появления надежной исследовательской и backtesting базы.
	owner: user
	status: parked
	target: revisit after backtesting foundation exists

## Done

История закрытых шагов ведется в [architecture/changelog.md](./architecture/changelog.md). Ниже остается компактный индекс выполненных backlog-задач в одном стиле.

### Phase 1

- `DONE-P1-01` Ввести базовый Binance Spot runtime с bootstrap, settings, client, strategy, risk, orders, state и journaling.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../main.py](../main.py), [../src/binance_bot/main.py](../src/binance_bot/main.py), [../src/binance_bot/config.py](../src/binance_bot/config.py), [../src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py), [../src/binance_bot/strategy/ema_cross.py](../src/binance_bot/strategy/ema_cross.py), [../src/binance_bot/risk/manager.py](../src/binance_bot/risk/manager.py), [../src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py), [../src/binance_bot/core/models.py](../src/binance_bot/core/models.py), [../src/binance_bot/core/state.py](../src/binance_bot/core/state.py), [../src/binance_bot/core/journal.py](../src/binance_bot/core/journal.py)
- `DONE-P1-02` Ввести базовые runtime adapters для logging и Telegram notifications.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../src/binance_bot/core/logging_setup.py](../src/binance_bot/core/logging_setup.py), [../src/binance_bot/notify/telegram.py](../src/binance_bot/notify/telegram.py)
- `DONE-P1-03` Ввести базовые docs, CI workflows и unit tests для strategy и risk.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../README.md](../README.md), [../.github/workflows/ci.yml](../.github/workflows/ci.yml), [../.github/workflows/run-bot.yml](../.github/workflows/run-bot.yml), [../tests/test_ema_cross.py](../tests/test_ema_cross.py), [../tests/test_risk_manager.py](../tests/test_risk_manager.py)

### Phase 2

- `DONE-P2-01` Вынести app run loop в runtime service и сделать bootstrap тонким.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../src/binance_bot/main.py](../src/binance_bot/main.py), [../src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py)
- `DONE-P2-02` Усилить тестовую базу для state store и order manager.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../tests/test_order_manager.py](../tests/test_order_manager.py), [../tests/test_state_store.py](../tests/test_state_store.py), [../tests/fakes.py](../tests/fakes.py)
- `DONE-P2-03` Стабилизировать test structure и CI flow для следующих рефакторингов.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../pyproject.toml](../pyproject.toml), [../tests](../tests), [../apply_tradingbot_test_fixes.sh](../apply_tradingbot_test_fixes.sh)

### Phase 3

- `DONE-P3-01` Ввести architecture overview и invariants для следующего слоя изменений.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [./architecture/system-overview.md](./architecture/system-overview.md), [./architecture/invariants.md](./architecture/invariants.md), [../AI_RULES.md](../AI_RULES.md)
- `DONE-P3-02` Вынести pure decision layer и упростить orchestration в cycle и position monitor.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py), [../src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py), [../src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py)
- `DONE-P3-03` Расширить service-level и decision-level tests для runtime orchestration.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../tests/test_decisions.py](../tests/test_decisions.py), [../tests/test_cycle.py](../tests/test_cycle.py), [../tests/test_position_monitor.py](../tests/test_position_monitor.py), [../tests/fakes.py](../tests/fakes.py)
- `DONE-P3-04` Исправить step-size rounding через общий helper и закрыть regression coverage.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../src/binance_bot/core/rounding.py](../src/binance_bot/core/rounding.py), [../src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py), [../tests/test_order_manager.py](../tests/test_order_manager.py)
- `DONE-P3-05` Починить test imports в CI и обновить README под текущую архитектуру.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../tests/__init__.py](../tests/__init__.py), [../README.md](../README.md), [../.github/workflows/ci.yml](../.github/workflows/ci.yml)

### Phase 4

- `DONE-P4-01` Вынести trade execution use-cases и порты в отдельный application layer.
	owner: copilot
	status: done
	target: 2026-03-19
	files: [../src/binance_bot/core/trade_execution.py](../src/binance_bot/core/trade_execution.py), [../src/binance_bot/use_cases/ports.py](../src/binance_bot/use_cases/ports.py), [../src/binance_bot/use_cases/trade_execution.py](../src/binance_bot/use_cases/trade_execution.py), [../src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py), [../tests/test_trade_execution.py](../tests/test_trade_execution.py)

### Phase 4.1

- `DONE-P4.1-01` Ввести reconciliation-aware state contract для blocked symbols, suspect positions и startup issues.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/core/models.py](../src/binance_bot/core/models.py), [../src/binance_bot/core/state.py](../src/binance_bot/core/state.py), [../src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py)
- `DONE-P4.1-02` Ввести exchange snapshot и recovery path через отдельный reconciliation service.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/clients/binance_client.py](../src/binance_bot/clients/binance_client.py), [../src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py), [../src/binance_bot/orders/manager.py](../src/binance_bot/orders/manager.py)
- `DONE-P4.1-03` Встроить reconciliation guardrails в runtime, cycle, risk manager и position monitor.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py), [../src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py), [../src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py), [../src/binance_bot/risk/manager.py](../src/binance_bot/risk/manager.py), [../src/binance_bot/main.py](../src/binance_bot/main.py)
- `DONE-P4.1-04` Закрыть reconciliation tests и отразить flow в архитектурной документации.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../tests/test_reconciliation.py](../tests/test_reconciliation.py), [./architecture/system-overview.md](./architecture/system-overview.md), [./architecture/invariants.md](./architecture/invariants.md), [../README.md](../README.md)

### Phase 4.2

- `DONE-P4.2-01` Ввести operator workflow для inspect, acknowledge, repair и unblock.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/main.py](../src/binance_bot/main.py), [../src/binance_bot/services/repair.py](../src/binance_bot/services/repair.py), [../src/binance_bot/core/decisions.py](../src/binance_bot/core/decisions.py), [../tests/test_repair.py](../tests/test_repair.py)
- `DONE-P4.2-02` Ввести runtime status service для inspect flow и operator reporting.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/services/status.py](../src/binance_bot/services/status.py), [../src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py), [../tests/test_status.py](../tests/test_status.py)
- `DONE-P4.2-03` Ввести repair journal, acknowledgement tracking, alert dedupe и operator playbook.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/config.py](../src/binance_bot/config.py), [../src/binance_bot/core/models.py](../src/binance_bot/core/models.py), [../src/binance_bot/services/reconciliation.py](../src/binance_bot/services/reconciliation.py), [./architecture/operator-playbook.md](./architecture/operator-playbook.md), [../docs/backlog.md](../docs/backlog.md)

### Phase 5

- `DONE-P5-01` Ввести safe runtime modes и runtime summaries для более безопасной эксплуатации.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/config.py](../src/binance_bot/config.py), [../src/binance_bot/services/runtime.py](../src/binance_bot/services/runtime.py), [../src/binance_bot/services/cycle.py](../src/binance_bot/services/cycle.py), [../src/binance_bot/services/position_monitor.py](../src/binance_bot/services/position_monitor.py), [../tests/test_cycle.py](../tests/test_cycle.py), [../tests/test_position_monitor.py](../tests/test_position_monitor.py)
- `DONE-P5-02` Ввести классификацию runtime errors и единый error-handling path.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../src/binance_bot/core/errors.py](../src/binance_bot/core/errors.py), [../src/binance_bot/services/error_handler.py](../src/binance_bot/services/error_handler.py)
- `DONE-P5-03` Ввести state regression fixtures и усилить CI/documentation под service smoke сценарии.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../tests/fixtures/legacy_state.json](../tests/fixtures/legacy_state.json), [../tests/fixtures/blocked_state.json](../tests/fixtures/blocked_state.json), [../tests/test_state_fixtures.py](../tests/test_state_fixtures.py), [../.github/workflows/ci.yml](../.github/workflows/ci.yml), [../README.md](../README.md), [../AI_RULES.md](../AI_RULES.md)

### Cross-phase

- `DONE-X-01` Ввести встроенный backlog как рабочий planning artifact для следующих итераций.
	owner: copilot
	status: done
	target: 2026-03-20
	files: [../docs/backlog.md](../docs/backlog.md)