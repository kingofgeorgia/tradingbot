# Binance Spot Trading Bot

Локальный торговый бот для Binance Spot на Python 3.11+.

## Возможности первой версии

- `APP_MODE=demo` для Binance Spot Testnet и `APP_MODE=live` для production.
- Пары `BTCUSDT` и `ETHUSDT`.
- Таймфрейм `15m`.
- Стратегия по пересечению `EMA(20)` и `EMA(50)`.
- Локальный `stop-loss 2%` и `take-profit 4%`.
- Ограничения риска: 1% риска на сделку, максимум 10% капитала на позицию, 2 открытые позиции суммарно, 1 позиция на инструмент, дневной лимит убытка 3%, остановка после 3 подряд убыточных сделок.
- Логи в консоль и файлы, CSV-журналы сигналов, сделок и ошибок.
- Telegram-уведомления о старте, сделках, API-ошибках и остановке торговли.

## Быстрый старт

1. Установите Python 3.11+.
2. Создайте виртуальное окружение.
3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Скопируйте `.env.example` в `.env` и заполните ключи.
5. Для безопасного старта используйте `APP_MODE=demo` и ключи от Binance Spot Testnet.
6. Запуск:

```bash
python main.py
```

## Структура

- `src/binance_bot/config.py` — загрузка конфигурации и путей.
- `src/binance_bot/clients/binance_client.py` — REST-клиент Binance Spot.
- `src/binance_bot/strategy/ema_cross.py` — EMA crossover стратегия.
- `src/binance_bot/risk/manager.py` — правила риск-менеджмента.
- `src/binance_bot/orders/manager.py` — открытие и закрытие ордеров.
- `src/binance_bot/notify/telegram.py` — Telegram-уведомления.
- `src/binance_bot/main.py` — основной цикл бота.

## Важно

- Не включайте права на вывод средств для API-ключей.
- Перед `APP_MODE=live` проверьте логику только в `demo`.
- В этой версии stop-loss и take-profit контролируются ботом локально, а не серверными OCO-ордерами.