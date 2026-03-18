# Схема проекта

main.py
└── src/binance_bot/main.py
    ├── config.py              # settings + runtime dirs
    ├── clients/               # Binance REST
    ├── core/                  # models, state, journals, logging
    ├── strategy/              # signal generation only
    ├── risk/                  # position/risk rules only
    ├── orders/                # open/close execution only
    └── notify/                # Telegram notifications only