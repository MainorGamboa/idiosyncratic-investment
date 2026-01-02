#!/usr/bin/env python3
import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper


def load_broker_config():
    config_path = Path(__file__).resolve().parents[1] / "CONFIG.json"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("broker", {})


def resolve_connection_settings():
    broker = load_broker_config()
    return {
        "host": os.getenv("IBKR_HOST", broker.get("host", "127.0.0.1")),
        "port": int(os.getenv("IBKR_PORT", broker.get("port", 4002))),
        "client_id": int(os.getenv("IBKR_CLIENT_ID", broker.get("client_id", 7))),
        "account": os.getenv("IBKR_ACCOUNT", broker.get("account", "")),
    }


class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self._ready = threading.Event()
        self._order_done = threading.Event()
        self._positions_done = threading.Event()
        self._mktdata_done = threading.Event()
        self._contract_details_done = threading.Event()
        self.order_status = {}
        self.positions = []
        self.market_data = {}
        self.contract_details = []
        self.errors = []

    def nextValidId(self, orderId):
        self.next_order_id = orderId
        self._ready.set()

    def error(self, reqId, errorCode, errorString):
        self.errors.append({"reqId": reqId, "code": errorCode, "message": errorString})

    def orderStatus(
        self,
        orderId,
        status,
        filled,
        remaining,
        avgFillPrice,
        permId,
        parentId,
        lastFillPrice,
        clientId,
        whyHeld,
        mktCapPrice,
    ):
        self.order_status[orderId] = {
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avgFillPrice": avgFillPrice,
            "lastFillPrice": lastFillPrice,
        }
        if status in {"Filled", "Cancelled", "Inactive"}:
            self._order_done.set()

    def position(self, account, contract, position, avgCost):
        self.positions.append(
            {
                "account": account,
                "symbol": contract.symbol,
                "secType": contract.secType,
                "currency": contract.currency,
                "position": position,
                "avgCost": avgCost,
            }
        )

    def positionEnd(self):
        self._positions_done.set()

    def tickPrice(self, reqId, tickType, price, attrib):
        self.market_data.setdefault(reqId, {})[tickType] = price
        if tickType in {1, 2, 4, 6}:  # bid, ask, last, high
            self._mktdata_done.set()

    def tickSnapshotEnd(self, reqId):
        self._mktdata_done.set()

    def contractDetails(self, reqId, contractDetails):
        self.contract_details.append(contractDetails)

    def contractDetailsEnd(self, reqId):
        self._contract_details_done.set()


def start_app(app, settings, timeout):
    app.connect(settings["host"], settings["port"], settings["client_id"])
    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()
    if not app._ready.wait(timeout):
        app.disconnect()
        raise RuntimeError("IBKR connection timed out waiting for nextValidId.")


def build_stock_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.primaryExchange = "NASDAQ"
    contract.currency = "USD"
    return contract


def build_order(action, quantity, order_type, limit_price, tif, account, override_constraints):
    order = Order()
    order.action = action
    order.totalQuantity = quantity
    order.orderType = order_type
    order.tif = tif
    # IBKR rejects unsupported attributes unless explicitly disabled.
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    if override_constraints:
        order.overridePercentageConstraints = True
    if order_type == "LMT":
        order.lmtPrice = limit_price
    if account:
        order.account = account
    return order


def resolve_contract(app, ticker, timeout, conid=None):
    if conid is not None:
        contract = Contract()
        contract.conId = int(conid)
        contract.exchange = "SMART"
        return contract

    app.contract_details = []
    app._contract_details_done.clear()
    contract = build_stock_contract(ticker)
    app.reqContractDetails(1, contract)
    app._contract_details_done.wait(timeout)
    if not app.contract_details:
        return contract

    # Prefer NASDAQ-listed contract when available.
    for details in app.contract_details:
        c = details.contract
        if c.primaryExchange == "NASDAQ" and c.currency == "USD":
            return c
    return app.contract_details[0].contract


def place_order(args):
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)

    contract = resolve_contract(app, args.ticker, args.timeout, args.conid)
    order = build_order(
        args.action,
        args.quantity,
        args.order_type,
        args.limit,
        args.tif,
        settings["account"],
        args.override_percentage_constraints,
    )

    order_id = app.next_order_id
    app.placeOrder(order_id, contract, order)

    app._order_done.wait(args.timeout)
    app.disconnect()

    result = {
        "order_id": order_id,
        "ticker": args.ticker,
        "action": args.action,
        "quantity": args.quantity,
        "order_type": args.order_type,
        "limit": args.limit,
        "tif": args.tif,
        "status": app.order_status.get(order_id, {}),
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


def list_positions(args):
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)
    app.reqPositions()
    app._positions_done.wait(args.timeout)
    app.disconnect()
    print(json.dumps({"positions": app.positions, "errors": app.errors}, indent=2))


def close_position(args):
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)
    app.reqPositions()
    app._positions_done.wait(args.timeout)

    match = None
    for position in app.positions:
        if position["symbol"].upper() == args.ticker.upper():
            match = position
            break

    if not match or match["position"] == 0:
        app.disconnect()
        print(
            json.dumps(
                {
                    "ticker": args.ticker,
                    "error": "No open position found for ticker.",
                    "positions_checked": app.positions,
                    "errors": app.errors,
                },
                indent=2,
            )
        )
        return

    quantity = abs(match["position"]) if args.quantity is None else args.quantity
    action = "SELL" if match["position"] > 0 else "BUY"
    contract = resolve_contract(app, args.ticker, args.timeout, args.conid)
    order = build_order(
        action,
        quantity,
        args.order_type,
        args.limit,
        args.tif,
        settings["account"],
        args.override_percentage_constraints,
    )

    order_id = app.next_order_id
    app.placeOrder(order_id, contract, order)
    app._order_done.wait(args.timeout)
    app.disconnect()

    result = {
        "order_id": order_id,
        "ticker": args.ticker,
        "action": action,
        "quantity": quantity,
        "order_type": args.order_type,
        "limit": args.limit,
        "tif": args.tif,
        "status": app.order_status.get(order_id, {}),
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


def quote(args):
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)
    contract = resolve_contract(app, args.ticker, args.timeout, args.conid)
    req_id = 1
    # Request delayed market data when live subscriptions aren't available.
    app.reqMarketDataType(4)
    app.reqMktData(req_id, contract, "", True, False, [])
    app._mktdata_done.wait(args.timeout)
    app.disconnect()

    ticks = app.market_data.get(req_id, {})
    result = {
        "ticker": args.ticker,
        "conid": getattr(contract, "conId", None) or None,
        "bid": ticks.get(1),
        "ask": ticks.get(2),
        "last": ticks.get(4),
        "high": ticks.get(6),
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


def resolve_contract_details(args):
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)
    app.contract_details = []
    app._contract_details_done.clear()
    contract = build_stock_contract(args.ticker)
    app.reqContractDetails(1, contract)
    app._contract_details_done.wait(args.timeout)
    app.disconnect()

    details = []
    for item in app.contract_details:
        c = item.contract
        details.append(
            {
                "conid": c.conId,
                "symbol": c.symbol,
                "secType": c.secType,
                "currency": c.currency,
                "exchange": c.exchange,
                "primaryExchange": c.primaryExchange,
                "localSymbol": c.localSymbol,
            }
        )

    print(json.dumps({"ticker": args.ticker, "contracts": details, "errors": app.errors}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description="IBKR paper trading helper (official ibapi).",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for IBKR responses.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    place = subparsers.add_parser("place", help="Place a BUY/SELL order.")
    place.add_argument("ticker", help="Ticker symbol, e.g. SRPT")
    place.add_argument("action", choices=["BUY", "SELL"], help="Order action.")
    place.add_argument("quantity", type=float, help="Share quantity.")
    place.add_argument("--order-type", choices=["MKT", "LMT"], default="MKT")
    place.add_argument("--limit", type=float, default=None, help="Limit price for LMT orders.")
    place.add_argument("--tif", default="DAY", help="Time in force.")
    place.add_argument("--conid", type=int, default=None, help="Override contract conId.")
    place.add_argument(
        "--override-percentage-constraints",
        action="store_true",
        help="Allow limits far from market (IBKR price band override).",
    )
    place.set_defaults(func=place_order)

    close = subparsers.add_parser("close", help="Close an existing position.")
    close.add_argument("ticker", help="Ticker symbol, e.g. SRPT")
    close.add_argument("--quantity", type=float, default=None, help="Override quantity to close.")
    close.add_argument("--order-type", choices=["MKT", "LMT"], default="MKT")
    close.add_argument("--limit", type=float, default=None, help="Limit price for LMT orders.")
    close.add_argument("--tif", default="DAY", help="Time in force.")
    close.add_argument("--conid", type=int, default=None, help="Override contract conId.")
    close.add_argument(
        "--override-percentage-constraints",
        action="store_true",
        help="Allow limits far from market (IBKR price band override).",
    )
    close.set_defaults(func=close_position)

    positions = subparsers.add_parser("positions", help="List open positions.")
    positions.set_defaults(func=list_positions)

    quote_cmd = subparsers.add_parser("quote", help="Fetch a market data snapshot.")
    quote_cmd.add_argument("ticker", help="Ticker symbol, e.g. SRPT")
    quote_cmd.add_argument("--conid", type=int, default=None, help="Override contract conId.")
    quote_cmd.set_defaults(func=quote)

    resolve_cmd = subparsers.add_parser("resolve", help="Resolve contract details.")
    resolve_cmd.add_argument("ticker", help="Ticker symbol, e.g. SRPT")
    resolve_cmd.set_defaults(func=resolve_contract_details)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.command in {"place", "close"} and args.order_type == "LMT" and args.limit is None:
        parser.error("--limit is required for LMT orders.")
    try:
        args.func(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
