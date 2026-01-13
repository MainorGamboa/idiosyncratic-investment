#!/usr/bin/env python3
"""
IBKR Paper Trading Interface for Options and Stocks.

This module provides a command-line interface to Interactive Brokers TWS/Gateway
for fetching market data, placing orders, and monitoring positions. It supports:

- Stock quotes and historical data
- Options quotes with Greeks (IV, delta, gamma, vega, theta)
- ATM IV discovery for PDUFA scoring
- Options and stock order placement
- Position monitoring

Data Type Handling:
    - Requests delayed market data (type 4) by default for backward compatibility
    - Auto-detects real-time vs delayed data based on tick types
    - Warns when using delayed data (OPRA subscription may be inactive)
    - With OPRA subscription active: Generic tick 106 provides real-time Greeks

Requirements:
    - IBKR TWS or Gateway running (default: 127.0.0.1:4002)
    - OPRA subscription for real-time options Greeks (optional, falls back to delayed)
    - Python packages: ibapi

Usage:
    python ibkr_paper.py quote SPY
    python ibkr_paper.py atm_iv SPY --expiration 2026-02-20
    python ibkr_paper.py quote_option SPY --strike 600 --expiration 2026-02-20 --right CALL
"""
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

from options_utils import determine_strike_increment, round_to_increment


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


# ============================================================================
# IBKR CLIENT & CALLBACKS
# ============================================================================


class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self._ready = threading.Event()
        self._order_done = threading.Event()
        self._positions_done = threading.Event()
        self._mktdata_done = threading.Event()
        self._contract_details_done = threading.Event()
        self._historical_done = threading.Event()
        self.order_status = {}
        self.positions = []
        self.market_data = {}
        self.contract_details = []
        self.historical_bars = []
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
        # Include delayed ticks (66/67/68/72) when using market data type 4.
        if tickType in {1, 2, 4, 6, 66, 67, 68, 72}:  # bid, ask, last, high
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
        """
        Handle Greeks data for options.

        Validates sentinel values and range checks to ensure data quality.
        IBKR uses -1 and -2 as "not available" sentinels.
        """
        def clean_greek(value, name, valid_range=None):
            """
            Clean and validate Greek value from IBKR.

            Args:
                value: Raw value from IBKR
                name: Greek name for logging
                valid_range: Optional tuple (min, max) for range validation

            Returns:
                Cleaned value or None if invalid
            """
            # IBKR sentinel values
            if value is None or value == -1 or value == -2:
                return None

            # Range validation
            if valid_range:
                min_val, max_val = valid_range
                if not (min_val <= value <= max_val):
                    import sys
                    print(
                        f"WARNING: {name}={value:.4f} outside range [{min_val}, {max_val}]",
                        file=sys.stderr
                    )
                    return None  # Don't use out-of-range values

            return value

        greeks = self.market_data.setdefault(reqId, {}).setdefault("greeks", {})

        # Clean and validate each Greek with appropriate ranges
        greeks["implied_volatility"] = clean_greek(impliedVol, "IV", (0.05, 5.0))  # 5% to 500% IV
        greeks["delta"] = clean_greek(delta, "Delta", (0.0, 1.0))  # Delta for calls: 0 to 1
        greeks["gamma"] = clean_greek(gamma, "Gamma", (0.0, 1.0))  # Gamma: 0 to 1
        greeks["vega"] = clean_greek(vega, "Vega", (0.0, 10.0))  # Vega: 0 to 10
        greeks["theta"] = clean_greek(theta, "Theta", (-10.0, 0.0))  # Theta for long: -10 to 0
        greeks["option_price"] = clean_greek(optPrice, "OptPrice", (0.0, 10000.0))  # Option price sanity
        greeks["underlying_price"] = clean_greek(undPrice, "UndPrice", (0.0, 100000.0))  # Stock price sanity

    def tickSnapshotEnd(self, reqId):
        self._mktdata_done.set()

    def contractDetails(self, reqId, contractDetails):
        self.contract_details.append(contractDetails)

    def contractDetailsEnd(self, reqId):
        self._contract_details_done.set()

    def historicalData(self, reqId, bar):
        """Callback for historical data bars."""
        self.historical_bars.append(
            {
                "date": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "wap": bar.wap,
                "barCount": bar.barCount,
            }
        )

    def historicalDataEnd(self, reqId, start, end):
        """Signal historical data request completion."""
        self._historical_done.set()


def start_app(app, settings, timeout):
    app.connect(settings["host"], settings["port"], settings["client_id"])
    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()
    if not app._ready.wait(timeout):
        app.disconnect()
        raise RuntimeError("IBKR connection timed out waiting for nextValidId.")


def _detect_data_type(ticks):
    """
    Detect if market data is real-time or delayed based on tick types.

    IBKR sends different tick types depending on whether the user has live
    subscriptions (e.g., OPRA for options) or is receiving delayed data.

    Real-time ticks: 1 (bid), 2 (ask), 4 (last), 6 (high)
    Delayed ticks: 66 (bid), 67 (ask), 68 (last), 72 (high)

    Args:
        ticks: Dict of tick data from app.market_data[req_id]

    Returns:
        str: "real-time", "delayed", or "unknown"
    """
    has_realtime = any(tick_type in ticks for tick_type in [1, 2, 4, 6])
    has_delayed = any(tick_type in ticks for tick_type in [66, 67, 68, 72])

    if has_delayed and not has_realtime:
        return "delayed"
    elif has_realtime:
        return "real-time"
    return "unknown"


# ============================================================================
# CONTRACT BUILDERS
# ============================================================================


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
    Build an option contract object for IBKR API requests.

    Args:
        symbol: Underlying stock ticker (e.g., "SPY")
        expiration: Expiration date as "YYYY-MM-DD" (converted to YYYYMMDD)
        strike: Strike price as float
        right: "CALL" or "PUT"
        exchange: Trading exchange, default "SMART" for best execution

    Returns:
        ibapi.contract.Contract configured for options

    Example:
        contract = build_option_contract("SPY", "2026-02-20", 600.0, "CALL")
        # Creates SPY Feb20'26 600 Call contract
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


# ============================================================================
# ORDER PLACEMENT
# ============================================================================


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


# ============================================================================
# MARKET DATA REQUESTS
# ============================================================================


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
    bid = ticks.get(1) or ticks.get(66)
    ask = ticks.get(2) or ticks.get(67)
    last = ticks.get(4) or ticks.get(68)
    high = ticks.get(6) or ticks.get(72)
    result = {
        "ticker": args.ticker,
        "conid": getattr(contract, "conId", None) or None,
        "bid": bid,
        "ask": ask,
        "last": last,
        "high": high,
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
    """
    Fetch single option quote with Greeks and pricing.

    Requests streaming market data for a specific option contract,
    waiting for Greeks (IV, delta, gamma, vega, theta) via generic
    tick "106" and pricing via standard ticks (bid/ask/last).

    Args:
        args: argparse.Namespace with:
            - ticker: Stock symbol
            - expiration: Option expiration (YYYY-MM-DD)
            - strike: Strike price
            - right: "CALL" or "PUT"
            - timeout: Request timeout in seconds

    Returns:
        Prints JSON to stdout with:
        - Pricing: bid, ask, last, mid_price
        - Liquidity: volume (tick 8), open_interest (tick 86)
        - Greeks: delta, gamma, vega, theta, implied_volatility
        - underlying_price: From Greeks computation
        - data_type: "real-time", "delayed", or "unknown"
        - source: "IBKR Paper"
        - errors: List of IBKR error messages

    Requirements:
        - OPRA subscription for real-time Greeks
        - Streaming mode (snapshot=False) required for generic ticks
    """
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
    # Request Greeks via generic tick 106 (IV, delta, gamma, vega, theta)
    app.reqMktData(req_id, contract, "106", False, False, [])
    app._mktdata_done.wait(args.timeout)
    app.disconnect()

    ticks = app.market_data.get(req_id, {})
    greeks = ticks.get("greeks", {})

    # Detect if we're getting real-time or delayed data
    data_type = _detect_data_type(ticks)
    if data_type == "delayed":
        print(
            f"WARNING: Using delayed data for {args.ticker} options (OPRA subscription may be inactive)",
            file=sys.stderr
        )

    bid = ticks.get(1) or ticks.get(66)  # Real-time or delayed bid
    ask = ticks.get(2) or ticks.get(67)  # Real-time or delayed ask
    last = ticks.get(4) or ticks.get(68)  # Real-time or delayed last
    mid_price = ((bid + ask) / 2) if (bid and ask) else None

    result = {
        "ticker": args.ticker,
        "strike": args.strike,
        "expiration": args.expiration,
        "right": args.right,
        "bid": bid,
        "ask": ask,
        "last": last,
        "mid_price": mid_price,
        "volume": ticks.get("size_8"),  # Size tick type 8 = volume
        "open_interest": ticks.get("size_86"),  # Size tick type 86 = OI
        "delta": greeks.get("delta"),
        "theta": greeks.get("theta"),
        "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"),
        "implied_volatility": greeks.get("implied_volatility"),
        "underlying_price": greeks.get("underlying_price"),
        "data_type": data_type,
        "source": "IBKR Paper",
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


def fetch_historical(args):
    """Fetch historical daily bars for a ticker."""
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)

    contract = resolve_contract(app, args.ticker, args.timeout, args.conid)

    app.historical_bars = []
    app._historical_done.clear()

    app.reqHistoricalData(
        1,
        contract,
        "",
        f"{args.days} D",
        "1 day",
        "TRADES",
        1,
        1,
        False,
        [],
    )

    if not app._historical_done.wait(args.timeout):
        app.disconnect()
        print(json.dumps({"error": "IBKR historical data timeout", "errors": app.errors}))
        sys.exit(1)

    app.disconnect()

    result = {
        "ticker": args.ticker,
        "bars": app.historical_bars,
        "count": len(app.historical_bars),
        "source": "IBKR Paper",
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


def fetch_atm_iv(args):
    """
    Fetch implied volatility from the nearest ATM call option.

    Algorithm:
    1. Fetch underlying price snapshot
    2. Calculate candidate strikes (base ± 1,2,3 increments)
    3. Loop through strikes requesting Greeks (generic tick 106)
    4. Select first strike with delta in [0.40, 0.60] (ATM range)
    5. Fallback to closest strike if no ATM found

    Strike increments are based on underlying price:
    - Price < $50: $2.50 increments
    - Price $50-$200: $5.00 increments
    - Price > $200: $10.00 increments

    Args:
        args: argparse.Namespace with:
            - ticker: Stock symbol (e.g., "SPY")
            - expiration: Option expiration date (YYYY-MM-DD)
            - underlying_price: Optional override for underlying price
            - timeout: Request timeout in seconds
            - conid: Optional contract ID override

    Returns:
        Prints JSON to stdout with:
        - implied_volatility: IV as decimal (e.g., 0.25 = 25%)
        - delta: Call delta (0.0-1.0)
        - strike: Selected strike price
        - underlying_price: Current stock price
        - is_atm: Boolean, True if delta in [0.40, 0.60]
        - data_type: "real-time", "delayed", or "unknown"
        - source: "IBKR Paper"
        - errors: List of IBKR error messages

    Requirements:
        - OPRA subscription active for real-time Greeks
        - Cannot use snapshot mode with generic tick "106"
        - Requires streaming data (snapshot=False)
    """
    settings = resolve_connection_settings()
    app = IBKRApp()
    start_app(app, settings, args.timeout)

    contract = resolve_contract(app, args.ticker, args.timeout, args.conid)

    # Fetch underlying price snapshot
    app._mktdata_done.clear()
    req_id = 1
    app.reqMarketDataType(4)
    app.reqMktData(req_id, contract, "", True, False, [])
    app._mktdata_done.wait(args.timeout)

    ticks = app.market_data.get(req_id, {})
    last = ticks.get(4) or ticks.get(68)
    bid = ticks.get(1) or ticks.get(66)
    ask = ticks.get(2) or ticks.get(67)
    underlying_price = last or ((bid + ask) / 2 if (bid and ask) else None)
    if underlying_price is None and args.underlying_price is not None:
        underlying_price = float(args.underlying_price)

    if underlying_price is None:
        app.disconnect()
        print(json.dumps({"error": "Missing underlying price", "errors": app.errors}))
        sys.exit(1)

    increment = determine_strike_increment(underlying_price)
    base_strike = round_to_increment(underlying_price, increment)

    candidate_strikes = [base_strike]
    max_steps = 3
    for offset in range(1, max_steps + 1):
        candidate_strikes.append(round(base_strike + offset * increment, 2))
        candidate_strikes.append(round(base_strike - offset * increment, 2))

    candidate_strikes = [strike for strike in candidate_strikes if strike > 0]

    selected = None
    selected_strike = None
    selected_delta = None
    selected_iv = None

    for strike in candidate_strikes:
        req_id += 1
        app._mktdata_done.clear()
        option_contract = build_option_contract(
            args.ticker,
            args.expiration,
            strike,
            "CALL",
        )
        app.reqMarketDataType(4)
        app.reqMktData(req_id, option_contract, "106", False, False, [])
        app._mktdata_done.wait(args.timeout)

        option_ticks = app.market_data.get(req_id, {})
        greeks = option_ticks.get("greeks", {})
        implied_vol = greeks.get("implied_volatility")
        delta = greeks.get("delta")

        if implied_vol is None:
            continue

        selected = option_ticks
        selected_strike = strike
        selected_delta = delta
        selected_iv = implied_vol

        if delta is not None and 0.40 <= delta <= 0.60:
            break

    app.disconnect()

    if selected is None:
        print(json.dumps({"error": "No options data available", "errors": app.errors}))
        sys.exit(1)

    if selected_delta is None or not (0.40 <= selected_delta <= 0.60):
        print(
            f"WARNING: Delta {selected_delta} outside ATM range for {args.ticker}",
            file=sys.stderr,
        )

    # Detect if we're getting real-time or delayed data
    data_type = _detect_data_type(selected)
    if data_type == "delayed":
        print(
            f"WARNING: Using delayed data for {args.ticker} options (OPRA subscription may be inactive)",
            file=sys.stderr
        )

    result = {
        "ticker": args.ticker,
        "strike": selected_strike,
        "expiration": args.expiration,
        "right": "CALL",
        "delta": selected_delta,
        "implied_volatility": selected_iv,
        "underlying_price": underlying_price,
        "is_atm": selected_delta is not None and 0.40 <= selected_delta <= 0.60,
        "data_type": data_type,
        "source": "IBKR Paper",
        "errors": app.errors,
    }
    print(json.dumps(result, indent=2))


# ============================================================================
# CLI ARGUMENT PARSING & MAIN
# ============================================================================


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

    historical_cmd = subparsers.add_parser("historical", help="Fetch historical daily bars.")
    historical_cmd.add_argument("ticker", help="Ticker symbol, e.g. SPY")
    historical_cmd.add_argument("--days", type=int, default=210, help="Calendar days of history to request.")
    historical_cmd.add_argument("--conid", type=int, default=None, help="Override contract conId.")
    historical_cmd.set_defaults(func=fetch_historical)

    atm_iv_cmd = subparsers.add_parser("atm_iv", help="Fetch IV from ATM options.")
    atm_iv_cmd.add_argument("ticker", help="Ticker symbol, e.g. SPY")
    atm_iv_cmd.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")
    atm_iv_cmd.add_argument("--underlying-price", type=float, default=None, help="Override underlying price.")
    atm_iv_cmd.add_argument("--conid", type=int, default=None, help="Override contract conId.")
    atm_iv_cmd.set_defaults(func=fetch_atm_iv)

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
