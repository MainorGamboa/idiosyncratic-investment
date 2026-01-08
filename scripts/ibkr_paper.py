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

    def tickSize(self, reqId, tickType, size):
        self.market_data.setdefault(reqId, {})[f"size_{tickType}"] = size

    def tickOptionComputation(
        self,
        reqId,
        tickType,
        tickAttrib,
        impliedVol,
        delta,
        optPrice,
        pvDividend,
        gamma,
        vega,
        theta,
        undPrice,
    ):
        """Handle Greeks data for options."""
        greeks = self.market_data.setdefault(reqId, {}).setdefault("greeks", {})
        greeks["implied_volatility"] = impliedVol if impliedVol and impliedVol != -1 and impliedVol != -2 else None
        greeks["delta"] = delta if delta and delta != -1 and delta != -2 else None
        greeks["gamma"] = gamma if gamma and gamma != -1 and gamma != -2 else None
        greeks["vega"] = vega if vega and vega != -1 and vega != -2 else None
        greeks["theta"] = theta if theta and theta != -1 and theta != -2 else None
        greeks["option_price"] = optPrice if optPrice and optPrice != -1 and optPrice != -2 else None
        greeks["underlying_price"] = undPrice if undPrice and undPrice != -1 and undPrice != -2 else None

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


def build_option_contract(symbol, expiration, strike, right="CALL", exchange="SMART"):
    """
    Build an option contract.

    Args:
        symbol: Underlying ticker symbol
        expiration: Expiration date (YYYY-MM-DD format, will be converted to YYYYMMDD)
        strike: Strike price
        right: "CALL" or "PUT"
        exchange: Exchange (default: SMART)

    Returns:
        Contract object for the option
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = exchange
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = expiration.replace("-", "")  # Convert YYYY-MM-DD to YYYYMMDD
    contract.strike = float(strike)
    contract.right = right.upper()
    contract.multiplier = "100"
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


def place_options_order(args):
    """Place an options order (long call/put)."""
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)

    # Build option contract
    contract = build_option_contract(
        args.ticker,
        args.expiration,
        args.strike,
        args.right
    )

    # Build order
    order = build_order(
        args.action,
        args.quantity,  # Number of contracts
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
        "strike": args.strike,
        "expiration": args.expiration,
        "right": args.right,
        "action": args.action,
        "contracts": args.quantity,
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


def quote_option(args):
    """Fetch option quote with Greeks."""
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)

    contract = build_option_contract(
        args.ticker,
        args.expiration,
        args.strike,
        args.right
    )

    req_id = 1
    # Request delayed market data when live subscriptions aren't available
    app.reqMarketDataType(4)
    # Request greeks by passing empty string for generic tick types
    app.reqMktData(req_id, contract, "106", False, False, [])  # 106 = option volume and open interest
    app._mktdata_done.wait(args.timeout)
    app.disconnect()

    ticks = app.market_data.get(req_id, {})
    greeks = ticks.get("greeks", {})

    bid = ticks.get(1)
    ask = ticks.get(2)
    mid_price = ((bid + ask) / 2) if (bid and ask) else None

    result = {
        "ticker": args.ticker,
        "strike": args.strike,
        "expiration": args.expiration,
        "right": args.right,
        "bid": bid,
        "ask": ask,
        "last": ticks.get(4),
        "mid_price": mid_price,
        "volume": ticks.get("size_8"),  # Size tick type 8 = volume
        "open_interest": ticks.get("size_86"),  # Size tick type 86 = OI
        "delta": greeks.get("delta"),
        "theta": greeks.get("theta"),
        "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"),
        "implied_volatility": greeks.get("implied_volatility"),
        "underlying_price": greeks.get("underlying_price"),
        "source": "IBKR Paper",
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


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

    quote_opt = subparsers.add_parser("quote_option", help="Fetch option quote with Greeks.")
    quote_opt.add_argument("ticker", help="Underlying ticker symbol, e.g. SRPT")
    quote_opt.add_argument("--strike", type=float, required=True, help="Strike price")
    quote_opt.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")
    quote_opt.add_argument("--right", choices=["CALL", "PUT"], default="CALL", help="Option right")
    quote_opt.set_defaults(func=quote_option)

    place_opt = subparsers.add_parser("place_option", help="Place an options order.")
    place_opt.add_argument("ticker", help="Underlying ticker symbol, e.g. SRPT")
    place_opt.add_argument("action", choices=["BUY", "SELL"], help="Order action.")
    place_opt.add_argument("quantity", type=float, help="Number of contracts.")
    place_opt.add_argument("--strike", type=float, required=True, help="Strike price")
    place_opt.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")
    place_opt.add_argument("--right", choices=["CALL", "PUT"], default="CALL", help="Option right")
    place_opt.add_argument("--order-type", choices=["MKT", "LMT"], default="LMT")
    place_opt.add_argument("--limit", type=float, default=None, help="Limit price for LMT orders.")
    place_opt.add_argument("--tif", default="DAY", help="Time in force.")
    place_opt.add_argument(
        "--override-percentage-constraints",
        action="store_true",
        help="Allow limits far from market (IBKR price band override).",
    )
    place_opt.set_defaults(func=place_options_order)

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
