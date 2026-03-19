# Архитектурные инварианты tradingbot

1. Strategy не делает сетевых вызовов и не отправляет ордера.
2. RiskManager не ходит в Binance API и не пишет в Telegram.
3. BinanceSpotClient не содержит торговых решений.
4. OrderManager не генерирует торговые сигналы.
5. StateStore — источник истины по локальному состоянию.
6. Любое изменение risk sizing, stop-loss, take-profit, daily loss limits — только вместе с тестами.
7. APP_MODE=live не используется без явного подтверждения и предварительной проверки в demo.
8. core/decisions.py содержит только pure decision logic без IO и внешних зависимостей.
9. services/* содержит orchestration и execution flow, но не источник торговых решений.
10. clients/, notify/ и journaling слои отвечают только за IO и не принимают торговых решений.
11. use_cases/* содержит application trade flows и возвращает явные результаты сценариев.
12. orders/manager.py остается тонким фасадом и не должен снова становиться контейнером бизнес-логики.
13. Startup reconciliation выполняется до первого process_cycle и является обязательным guardrail перед execution.
14. blocked symbol не участвует в process_cycle, пока mismatch не снят явным reconciliation-проходом.
15. services/reconciliation.py — единственная точка recovery-логики; она не должна расползаться по risk, strategy и clients.
16. services/repair.py выполняет только operator-driven repair actions и не должен быть частью обычного trading loop.
17. Runtime modes не должны молча менять торговую логику: любые ограничения execution должны явно логироваться.