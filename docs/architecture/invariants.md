# Архитектурные инварианты tradingbot

1. Strategy не делает сетевых вызовов и не отправляет ордера.
2. RiskManager не ходит в Binance API и не пишет в Telegram.
3. BinanceSpotClient не содержит торговых решений.
4. OrderManager не генерирует торговые сигналы.
5. StateStore — источник истины по локальному состоянию.
6. Любое изменение risk sizing, stop-loss, take-profit, daily loss limits — только вместе с тестами.
7. APP_MODE=live не используется без явного подтверждения и предварительной проверки в demo.