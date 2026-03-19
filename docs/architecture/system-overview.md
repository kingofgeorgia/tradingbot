# Схема проекта

main.py
└── src/binance_bot/main.py
    ├── config.py              # settings + runtime dirs
    ├── clients/               # Binance REST
    ├── core/                  # models, state, journals, logging, pure decisions
    ├── strategy/              # signal generation only
    ├── risk/                  # position/risk rules only
    ├── orders/                # thin facade over trade execution
    ├── use_cases/             # application-level trade execution flows
    ├── services/              # orchestration, runtime, reconciliation, repair, status
    └── notify/                # Telegram notifications only

## Границы ответственности

- core/decisions.py — pure decision helpers без API, notifier, state persistence и journal writes.
- services/runtime.py — composition root и lifecycle loop.
- services/reconciliation.py — startup reconciliation, state recovery и symbol blocking guardrail.
- services/repair.py — manual repair, acknowledgement и unblock flow для operator path.
- services/status.py — runtime status/reporting для observability и operator tooling.
- services/cycle.py — orchestration одного торгового цикла и coordination между зависимостями.
- services/position_monitor.py — исполнение решений по открытым позициям.
- services/error_handler.py — единая запись API ошибок и уведомлений.
- use_cases/trade_execution.py — open/close position use-cases с явными входами и результатами.
- adapters (clients/, notify/, journals) — только IO.