from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any
from urllib.parse import urlencode

import requests

from binance_bot.config import Settings
from binance_bot.core.models import Candle, SymbolFilters


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns an API or transport error."""


class BinanceSpotClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": settings.binance_api_key})
        self._time_offset_ms = 0
        self._exchange_filters_cache: dict[str, SymbolFilters] = {}

    def sync_time(self) -> None:
        server_time = self.get_server_time()
        local_time = int(time.time() * 1000)
        self._time_offset_ms = server_time - local_time

    def get_server_time(self) -> int:
        payload = self._request("GET", "/api/v3/time")
        return int(payload["serverTime"])

    def get_account(self) -> dict[str, Any]:
        return self._request("GET", "/api/v3/account", signed=True)

    def get_klines(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        payload = self._request(
            "GET",
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        candles: list[Candle] = []
        for index, row in enumerate(payload):
            candles.append(
                Candle(
                    open_time=int(row[0]),
                    open_price=float(row[1]),
                    high_price=float(row[2]),
                    low_price=float(row[3]),
                    close_price=float(row[4]),
                    volume=float(row[5]),
                    close_time=int(row[6]),
                    is_closed=index < len(payload) - 1,
                )
            )
        return candles

    def get_latest_price(self, symbol: str) -> float:
        payload = self._request("GET", "/api/v3/ticker/price", params={"symbol": symbol})
        return float(payload["price"])

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        if symbol in self._exchange_filters_cache:
            return self._exchange_filters_cache[symbol]
        payload = self._request("GET", "/api/v3/exchangeInfo", params={"symbol": symbol})
        symbol_info = payload["symbols"][0]
        filters = {item["filterType"]: item for item in symbol_info["filters"]}
        parsed_filters = SymbolFilters(
            step_size=float(filters["LOT_SIZE"]["stepSize"]),
            min_qty=float(filters["LOT_SIZE"]["minQty"]),
            min_notional=float(filters.get("MIN_NOTIONAL", {}).get("minNotional", 0.0)),
            tick_size=float(filters["PRICE_FILTER"]["tickSize"]),
        )
        self._exchange_filters_cache[symbol] = parsed_filters
        return parsed_filters

    def get_asset_free_balance(self, asset: str) -> float:
        account = self.get_account()
        for balance in account.get("balances", []):
            if balance["asset"] == asset:
                return float(balance["free"])
        return 0.0

    def get_asset_total_balance(self, asset: str) -> float:
        account = self.get_account()
        for balance in account.get("balances", []):
            if balance["asset"] == asset:
                return float(balance["free"]) + float(balance["locked"])
        return 0.0

    def get_portfolio_value(self, symbols: list[str], quote_asset: str) -> float:
        account = self.get_account()
        balances = {item["asset"]: float(item["free"]) + float(item["locked"]) for item in account.get("balances", [])}
        total_value = balances.get(quote_asset, 0.0)
        for symbol in symbols:
            if not symbol.endswith(quote_asset):
                continue
            base_asset = symbol[: -len(quote_asset)]
            asset_balance = balances.get(base_asset, 0.0)
            if asset_balance <= 0:
                continue
            total_value += asset_balance * self.get_latest_price(symbol)
        return total_value

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": self.format_quantity(quantity),
            "newOrderRespType": "FULL",
        }
        return self._request("POST", "/api/v3/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v3/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def confirm_order_filled(self, symbol: str, order_id: int, timeout_seconds: int) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        latest_payload: dict[str, Any] | None = None
        while time.time() < deadline:
            latest_payload = self.get_order(symbol, order_id)
            if latest_payload.get("status") == "FILLED":
                return latest_payload
            time.sleep(2)
        raise BinanceAPIError(
            f"Order {order_id} for {symbol} was not confirmed as FILLED within {timeout_seconds} seconds."
        )

    @staticmethod
    def calculate_average_fill_price(order_payload: dict[str, Any]) -> float:
        executed_qty = float(order_payload.get("executedQty", 0.0))
        cumulative_quote_qty = float(order_payload.get("cummulativeQuoteQty", 0.0))
        if executed_qty <= 0:
            raise BinanceAPIError("Executed quantity is zero; cannot calculate average fill price.")
        return cumulative_quote_qty / executed_qty

    @staticmethod
    def calculate_quote_fee(order_payload: dict[str, Any], quote_asset: str) -> float:
        fee_paid_quote = 0.0
        for fill in order_payload.get("fills", []):
            if fill.get("commissionAsset") == quote_asset:
                fee_paid_quote += float(fill.get("commission", 0.0))
        return fee_paid_quote

    @staticmethod
    def format_quantity(quantity: float) -> str:
        return format(Decimal(str(quantity)).normalize(), "f")

    @staticmethod
    def round_step_size(value: float, step_size: float) -> float:
        if step_size <= 0:
            return value
        quantized = Decimal(str(value)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN)
        return float(quantized)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        signed: bool = False,
    ) -> Any:
        prepared_params = dict(params or {})
        if signed:
            prepared_params["timestamp"] = int(time.time() * 1000) + self._time_offset_ms
            prepared_params["recvWindow"] = self._settings.binance_recv_window
            prepared_params["signature"] = self._sign(prepared_params)

        url = f"{self._settings.base_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=prepared_params if method.upper() == "GET" else None,
                data=prepared_params if method.upper() != "GET" else None,
                timeout=self._settings.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise BinanceAPIError(f"Transport error while calling Binance: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BinanceAPIError(f"Non-JSON response from Binance: {response.text}") from exc

        if response.status_code >= 400:
            message = payload.get("msg") if isinstance(payload, dict) else response.text
            raise BinanceAPIError(f"Binance API error {response.status_code}: {message}")
        if isinstance(payload, dict) and payload.get("code", 0) not in (0, None):
            raise BinanceAPIError(f"Binance API error {payload['code']}: {payload.get('msg', 'Unknown error')}")
        return payload

    def _sign(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        digest = hmac.new(
            self._settings.binance_secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()