# Схема проекта

main.py
└── src/binance_bot/main.py
    ├── config.py              # settings + runtime dirs
    ├── clients/               # Binance REST
    ├── core/                  # models, state, journals, logging, pure decisions
    ├── strategy/              # signal generation only
    ├── risk/                  # position/risk rules only
    ├── orders/                # open/close execution only
    └── notify/                # Telegram notifications only

## Границы ответственности

- core/decisions.py — pure decision helpers без API, notifier, state persistence и journal writes.
- services/runtime.py — composition root и lifecycle loop.
- services/cycle.py — orchestration одного торгового цикла и coordination между зависимостями.
- services/position_monitor.py — исполнение решений по открытым позициям.
- services/error_handler.py — единая запись API ошибок и уведомлений.
- adapters (clients/, notify/, journals) — только IO.