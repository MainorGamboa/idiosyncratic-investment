"""
Price Data Sources Module

Fetches price data from multiple sources with graceful degradation:
1. IBKR Paper (real-time)
2. Stooq (15-min delay)
3. Yahoo Finance (fallback)

Includes caching to avoid redundant API calls.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests

class PriceCache:
    """In-memory cache for price data with TTL."""

    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Tuple[Dict, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, ticker: str) -> Optional[Dict]:
        """Get cached price if still valid."""
        if ticker in self.cache:
            data, timestamp = self.cache[ticker]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                # Expired, remove from cache
                del self.cache[ticker]
        return None

    def set(self, ticker: str, data: Dict):
        """Cache price data with current timestamp."""
        self.cache[ticker] = (data, datetime.now())

    def clear(self):
        """Clear all cached data."""
        self.cache.clear()


# Global cache instance
_price_cache = PriceCache()


def fetch_from_ibkr(ticker: str) -> Optional[Dict]:
    """
    Fetch price from IBKR paper trading account.

    Uses existing ibkr_paper.py script.

    Returns:
        Dict with keys: price, bid, ask, last, timestamp, source
        None if fetch fails
    """
    try:
        script_path = Path(__file__).parent / "ibkr_paper.py"

        result = subprocess.run(
            [sys.executable, str(script_path), "quote", ticker],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"IBKR fetch failed for {ticker}: {result.stderr}", file=sys.stderr)
            return None

        # Parse JSON output from ibkr_paper.py
        data = json.loads(result.stdout)

        if "error" in data or not data.get("last"):
            return None

        return {
            "price": data.get("last"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "last": data.get("last"),
            "timestamp": datetime.now().isoformat(),
            "source": "IBKR Paper"
        }

    except subprocess.TimeoutExpired:
        print(f"IBKR fetch timeout for {ticker}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"IBKR JSON parse error for {ticker}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"IBKR fetch error for {ticker}: {e}", file=sys.stderr)
        return None


def fetch_from_stooq(ticker: str) -> Optional[Dict]:
    """
    Fetch price from Stooq (15-minute delay).

    Stooq API: https://stooq.com/q/d/l/?s={ticker}.us&i=d

    Returns:
        Dict with keys: price, timestamp, source
        None if fetch fails
    """
    try:
        # Stooq uses ticker + .us suffix for US stocks
        url = f"https://stooq.com/q/l/?s={ticker}.us&f=sd2t2ohlcv&h&e=json"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data or "symbols" not in data or not data["symbols"]:
            return None

        symbol_data = data["symbols"][0]

        if not symbol_data.get("close"):
            return None

        return {
            "price": float(symbol_data["close"]),
            "open": float(symbol_data.get("open", 0)),
            "high": float(symbol_data.get("high", 0)),
            "low": float(symbol_data.get("low", 0)),
            "volume": int(symbol_data.get("volume", 0)),
            "timestamp": datetime.now().isoformat(),
            "source": "Stooq (15-min delay)"
        }

    except requests.RequestException as e:
        print(f"Stooq fetch error for {ticker}: {e}", file=sys.stderr)
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Stooq data parse error for {ticker}: {e}", file=sys.stderr)
        return None


def fetch_from_yahoo(ticker: str) -> Optional[Dict]:
    """
    Fetch price from Yahoo Finance.

    Note: This uses a simple HTTP request to Yahoo Finance quote API.
    For production, consider using yfinance library.

    Returns:
        Dict with keys: price, timestamp, source
        None if fetch fails
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            "range": "1d",
            "interval": "1m"
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "chart" not in data or "result" not in data["chart"]:
            return None

        result = data["chart"]["result"][0]
        meta = result.get("meta", {})

        current_price = meta.get("regularMarketPrice")

        if not current_price:
            return None

        return {
            "price": float(current_price),
            "previous_close": float(meta.get("previousClose", 0)),
            "open": float(meta.get("regularMarketOpen", 0)),
            "day_high": float(meta.get("regularMarketDayHigh", 0)),
            "day_low": float(meta.get("regularMarketDayLow", 0)),
            "volume": int(meta.get("regularMarketVolume", 0)),
            "timestamp": datetime.now().isoformat(),
            "source": "Yahoo Finance"
        }

    except requests.RequestException as e:
        print(f"Yahoo fetch error for {ticker}: {e}", file=sys.stderr)
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Yahoo data parse error for {ticker}: {e}", file=sys.stderr)
        return None


def fetch_price(ticker: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Fetch price with graceful degradation across sources.

    Priority order:
    1. Check cache (if use_cache=True)
    2. Try IBKR Paper
    3. Try Stooq
    4. Try Yahoo Finance
    5. Return None if all fail

    Args:
        ticker: Stock ticker symbol
        use_cache: Whether to check cache first (default: True)

    Returns:
        Dict with price data and source, or None if all sources fail
    """
    ticker = ticker.upper()

    # Check cache first
    if use_cache:
        cached = _price_cache.get(ticker)
        if cached:
            cached["cache_hit"] = True
            return cached

    # Try sources in order
    sources = [
        ("IBKR Paper", fetch_from_ibkr),
        ("Stooq", fetch_from_stooq),
        ("Yahoo Finance", fetch_from_yahoo)
    ]

    for source_name, fetch_func in sources:
        try:
            data = fetch_func(ticker)
            if data:
                data["cache_hit"] = False
                # Cache successful fetch
                _price_cache.set(ticker, data)
                return data
        except Exception as e:
            print(f"{source_name} error for {ticker}: {e}", file=sys.stderr)
            continue

    # All sources failed
    print(f"ERROR: All price sources failed for {ticker}", file=sys.stderr)
    return None


def get_bid_ask_midpoint(ticker: str) -> Optional[float]:
    """
    Get bid/ask midpoint for limit order pricing.

    Returns:
        Midpoint price, or None if unavailable
    """
    data = fetch_price(ticker)

    if not data:
        return None

    # Try to calculate from bid/ask
    if "bid" in data and "ask" in data and data["bid"] and data["ask"]:
        return (data["bid"] + data["ask"]) / 2

    # Fallback to last price
    return data.get("price")


def main():
    """CLI interface for testing price fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch stock price from multiple sources")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache and fetch fresh data")
    parser.add_argument("--source", choices=["ibkr", "stooq", "yahoo"], help="Force specific source")
    parser.add_argument("--midpoint", action="store_true", help="Get bid/ask midpoint")

    args = parser.parse_args()

    if args.source:
        # Force specific source
        source_map = {
            "ibkr": fetch_from_ibkr,
            "stooq": fetch_from_stooq,
            "yahoo": fetch_from_yahoo
        }
        data = source_map[args.source](args.ticker.upper())
    elif args.midpoint:
        midpoint = get_bid_ask_midpoint(args.ticker)
        if midpoint:
            print(json.dumps({"midpoint": midpoint}, indent=2))
        else:
            print("ERROR: Could not get bid/ask midpoint", file=sys.stderr)
            sys.exit(1)
        return
    else:
        # Use graceful degradation
        data = fetch_price(args.ticker, use_cache=not args.no_cache)

    if data:
        print(json.dumps(data, indent=2))
    else:
        print(f"ERROR: Could not fetch price for {args.ticker}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
