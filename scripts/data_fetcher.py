"""
Data Fetcher Module

Main interface for fetching all data needed by trading skills.
Aggregates data from multiple sources:
- Price data (IBKR, Stooq, Yahoo)
- Financial data (SEC API)
- Market data (200-day MA, volume, IV)

Used by analyze, score, and monitor skills.
"""

import calendar
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, date

# Import local modules
from price_sources import fetch_price, fetch_historical_yahoo, get_bid_ask_midpoint
from sec_api import (
    parse_financials,
    fetch_two_periods,
    calculate_m_score,
    calculate_z_score,
    get_cik_from_ticker
)

# Note: Archetype-specific data (Form 483, EMA approval, insider clusters, WARN filings)
# requires manual lookup by the agent. The utility scripts (regulatory_data.py,
# insider_analysis.py, warn_act_checker.py) provide helper functions and lookup
# instructions, but do not have automated data fetching for these sources.
# Import data quality monitor
from data_quality_monitor import get_monitor


def _calculate_ma_200(bars: list) -> Optional[float]:
    """Calculate 200-day moving average from bar data."""
    closes = [
        bar.get("close")
        for bar in bars
        if bar.get("close") is not None and bar.get("close") >= 0
    ]
    if len(closes) < 200:
        return None
    recent = closes[-200:]
    return sum(recent) / 200


def _fetch_ma_200(ticker: str, days: int = 210) -> Optional[Dict]:
    """Fetch MA-200 from IBKR with Yahoo fallback."""
    script_path = Path(__file__).parent / "ibkr_paper.py"

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "historical",
                ticker,
                "--days",
                str(days),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(f"IBKR historical timeout for {ticker}", file=sys.stderr)
        result = None

    bars = []
    source = None

    if result and result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            bars = data.get("bars", []) or []
            source = data.get("source", "IBKR Paper")
        except json.JSONDecodeError as e:
            print(f"IBKR historical JSON parse error for {ticker}: {e}", file=sys.stderr)

    if bars:
        bars_sorted = sorted(bars, key=lambda b: b.get("date", ""))
        ma_200 = _calculate_ma_200(bars_sorted)
        if ma_200 is not None:
            return {
                "ma_200": ma_200,
                "source": source or "IBKR Paper",
                "bars_used": 200,
                "bars_total": len(bars_sorted),
            }

    # Yahoo fallback
    yahoo_bars = fetch_historical_yahoo(ticker, days=days)
    if yahoo_bars:
        bars_sorted = sorted(yahoo_bars, key=lambda b: b.get("date", ""))
        ma_200 = _calculate_ma_200(bars_sorted)
        if ma_200 is not None:
            return {
                "ma_200": ma_200,
                "source": "Yahoo Finance",
                "bars_used": 200,
                "bars_total": len(bars_sorted),
            }

    return None


def _is_atm_delta(delta: Optional[float]) -> bool:
    """Check if delta is within ATM range for calls."""
    if delta is None:
        return False
    return 0.40 <= delta <= 0.60


def _fetch_atm_iv(
    ticker: str,
    expiration: Optional[str] = None,
    underlying_price: Optional[float] = None,
) -> Optional[Dict]:
    """Fetch implied volatility from ATM option via IBKR."""
    expiration = expiration or _calculate_next_monthly_expiration()
    script_path = Path(__file__).parent / "ibkr_paper.py"

    cmd = [
        sys.executable,
        str(script_path),
        "atm_iv",
        ticker,
        "--expiration",
        expiration,
    ]
    if underlying_price is not None:
        cmd.extend(["--underlying-price", str(underlying_price)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print(f"IBKR IV timeout for {ticker}", file=sys.stderr)
        return None

    if result.returncode != 0:
        error_detail = result.stderr.strip()
        if not error_detail and result.stdout:
            try:
                error_payload = json.loads(result.stdout)
                error_detail = error_payload.get("error") or error_payload
            except json.JSONDecodeError:
                error_detail = result.stdout.strip()
        print(f"IBKR IV fetch failed for {ticker}: {error_detail}", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"IBKR IV JSON parse error for {ticker}: {e}", file=sys.stderr)
        return None

    if "error" in data:
        return None

    implied_vol = data.get("implied_volatility")
    delta = data.get("delta")
    strike = data.get("strike")
    underlying_price = data.get("underlying_price")

    monitor = get_monitor()
    iv_min, iv_max = monitor.greeks_validation["iv_range"]
    if implied_vol is None or not (iv_min <= implied_vol <= iv_max):
        print(f"IV {implied_vol} outside range for {ticker}", file=sys.stderr)
        return None

    is_atm = _is_atm_delta(delta)
    if delta is not None and not is_atm:
        print(f"WARNING: Delta {delta} outside ATM range for {ticker}", file=sys.stderr)

    if underlying_price and strike:
        distance_pct = abs(strike - underlying_price) / underlying_price
        if distance_pct > 0.05:
            print(
                f"WARNING: Strike {strike} is {distance_pct*100:.1f}% from price {underlying_price}",
                file=sys.stderr,
            )

    return {
        "implied_volatility": implied_vol,
        "source": data.get("source", "IBKR Paper"),
        "strike": strike,
        "delta": delta,
        "is_atm": is_atm,
    }


def _calculate_next_monthly_expiration() -> str:
    """Calculate the next monthly options expiration (3rd Friday)."""
    today = datetime.now().date()
    year = today.year
    month = today.month

    def third_friday(target_year: int, target_month: int) -> date:
        weeks = calendar.monthcalendar(target_year, target_month)
        fridays = [week[calendar.FRIDAY] for week in weeks if week[calendar.FRIDAY] != 0]
        return datetime(target_year, target_month, fridays[2]).date()

    expiration = third_friday(year, month)
    if expiration <= today:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        expiration = third_friday(year, month)

    return expiration.isoformat()


def fetch_all(ticker: str, industry: str = "general", archetype: str = "general") -> Dict:
    """
    Fetch ALL data needed for /analyze skill (kill screens).

    Data fetched:
    - Current price
    - M-Score (earnings manipulation) OR PDUFA financial health
    - Z-Score (bankruptcy risk) OR PDUFA financial health
    - Market cap
    - Financial metrics

    Args:
        ticker: Stock ticker symbol
        industry: Industry for Z-Score adjustment (biotech, software, utilities, general)
        archetype: Trade archetype (pdufa, merger_arb, activist, etc.)

    Returns:
        Dict with all fetched data and kill screen pass/fail status
    """
    ticker = ticker.upper()
    result = {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "data_sources_used": [],
        "errors": []
    }

    # 1. Fetch price data
    price_data = fetch_price(ticker)
    if price_data:
        result["price"] = price_data["price"]
        result["price_source"] = price_data["source"]
        result["data_sources_used"].append(price_data["source"])
    else:
        result["price"] = None
        result["errors"].append(f"Could not fetch price for {ticker}")

    # 2. Fetch financial data from SEC (TWO periods for M-Score)
    current_financials, prev_financials = fetch_two_periods(ticker)
    if current_financials:
        result["data_sources_used"].append(current_financials.source)

        # Calculate market cap (price * shares outstanding)
        if result.get("price") and current_financials.shares_outstanding > 0:
            market_cap = result["price"] * current_financials.shares_outstanding
            current_financials.market_cap = market_cap
            result["market_cap"] = market_cap
        else:
            result["market_cap"] = None

        # Apply archetype-specific kill screens
        if archetype.lower() == "pdufa":
            # PDUFA-specific financial health screens (for pre-revenue biotechs)
            result["archetype"] = "pdufa"
            result["kill_screen_type"] = "pdufa_financial_health"

            # Skip traditional M-Score/Z-Score for PDUFA trades
            result["m_score"] = None
            result["m_score_note"] = "Skipped for PDUFA archetype (pre-revenue biotech)"
            result["z_score"] = None
            result["z_score_note"] = "Skipped for PDUFA archetype (pre-revenue biotech)"

            # Calculate PDUFA-specific screens
            # 1. Cash runway (assume quarterly burn rate from operating cash flow)
            quarterly_burn = abs(current_financials.operating_cash_flow) / 4 if current_financials.operating_cash_flow < 0 else 0
            cash_runway_months = (current_financials.cash_and_equivalents / quarterly_burn * 3) if quarterly_burn > 0 else 999

            # 2. Debt-to-equity ratio
            equity = current_financials.total_assets - current_financials.total_liabilities
            debt_to_equity = current_financials.long_term_debt / equity if equity > 0 else 999

            # 3. Net cash position (cash - debt)
            net_cash = current_financials.cash_and_equivalents - current_financials.long_term_debt

            result["pdufa_financial_health"] = {
                "cash_runway_months": round(cash_runway_months, 1),
                "cash_runway_threshold": 18,
                "cash_runway_pass": cash_runway_months >= 18,
                "debt_to_equity": round(debt_to_equity, 2),
                "debt_to_equity_threshold": 0.75,
                "debt_to_equity_pass": debt_to_equity < 0.75,
                "net_cash": net_cash,
                "net_cash_pass": net_cash > 0,
                "cash_and_equivalents": current_financials.cash_and_equivalents,
                "long_term_debt": current_financials.long_term_debt
            }

            # Overall PDUFA financial health pass/fail
            pdufa_pass = (
                result["pdufa_financial_health"]["cash_runway_pass"] and
                result["pdufa_financial_health"]["debt_to_equity_pass"] and
                result["pdufa_financial_health"]["net_cash_pass"]
            )
            result["pdufa_financial_health"]["overall_pass"] = pdufa_pass

            # Use PDUFA screens for final pass/fail
            result["financial_screens_pass"] = pdufa_pass

        else:
            # Traditional M-Score and Z-Score for non-PDUFA archetypes
            result["archetype"] = archetype
            result["kill_screen_type"] = "traditional"

            # Calculate M-Score (requires TWO periods)
            m_score = calculate_m_score(current_financials, prev_financials)
            result["m_score"] = m_score
            result["m_score_threshold"] = -1.78
            result["m_score_pass"] = m_score is not None and m_score <= -1.78

            # Calculate Z-Score
            z_score = calculate_z_score(current_financials, industry)
            result["z_score"] = z_score

            # Industry-adjusted Z-Score threshold
            z_thresholds = {
                "biotech": 1.5,
                "pharma": 1.5,
                "software": 2.0,
                "saas": 2.0,
                "utilities": 2.5,
                "general": 1.81
            }
            z_threshold = z_thresholds.get(industry.lower(), 1.81)
            result["z_score_threshold"] = z_threshold
            result["z_score_pass"] = z_score is not None and z_score >= z_threshold

            # Use traditional screens for final pass/fail
            result["financial_screens_pass"] = (
                result.get("m_score_pass", False) and
                result.get("z_score_pass", False)
            )

        # Include key financial metrics
        result["financials"] = {
            "total_assets": current_financials.total_assets,
            "total_liabilities": current_financials.total_liabilities,
            "working_capital": current_financials.working_capital,
            "revenue": current_financials.revenue,
            "ebit": current_financials.ebit,
            "net_income": current_financials.net_income,
            "shares_outstanding": current_financials.shares_outstanding
        }

    else:
        result["errors"].append(f"Could not fetch financials for {ticker}")
        result["m_score"] = None
        result["z_score"] = None
        result["financial_screens_pass"] = False

    # 3. Archetype-specific notes (manual lookup required by agent)
    # See utility scripts for lookup instructions:
    # - regulatory_data.py: Form 483, EMA approval, CRL classification
    # - insider_analysis.py: Insider cluster validation
    # - warn_act_checker.py: WARN Act filings
    archetype_lower = archetype.lower()

    if archetype_lower == "pdufa":
        result["manual_checks_required"] = [
            "Form 483 with OAI status (FDA FOIA Reading Room)",
            "EMA approval status (ema.europa.eu/medicines)",
            "CRL classification if applicable"
        ]
    elif archetype_lower == "insider":
        result["manual_checks_required"] = [
            "Insider cluster validation (OpenInsider.com)",
            "Routine vs opportunistic classification (3-year Form 4 history)"
        ]
    elif archetype_lower in ["activist", "spinoff"]:
        result["manual_checks_required"] = [
            "WARN Act filings (state labor department databases)",
            "Contract loss language analysis if WARN found"
        ]
    elif archetype_lower == "merger_arb":
        result["manual_checks_required"] = [
            "Second request status (FTC/DOJ)",
            "CFIUS exposure",
            "China-connected buyer risk"
        ]

    # 4. Summary
    # Note: Archetype-specific kill screens (insider cluster, WARN filings)
    # require manual validation by the agent
    kill_screens_passed = result.get("financial_screens_pass", False)
    result["kill_screens_status"] = "PASS" if kill_screens_passed else "FAIL"

    return result


def fetch_market_data(ticker: str) -> Optional[Dict]:
    """
    Fetch market data for /score and /monitor skills.

    Data fetched:
    - Current price
    - 200-day moving average (approximation)
    - Volume
    - Implied Volatility (if available)

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with market data, or None if fetch fails
    """
    ticker = ticker.upper()

    price_data = fetch_price(ticker)

    if not price_data:
        return None

    result = {
        "ticker": ticker,
        "price": price_data["price"],
        "volume": price_data.get("volume", 0),
        "timestamp": datetime.now().isoformat(),
        "source": price_data["source"]
    }

    ma_200_data = _fetch_ma_200(ticker)
    if ma_200_data:
        result["ma_200"] = ma_200_data["ma_200"]
        result["ma_200_source"] = ma_200_data["source"]
        result["ma_200_bars_used"] = ma_200_data["bars_used"]
        result["ma_200_bars_total"] = ma_200_data.get("bars_total")
    else:
        result["ma_200"] = None
        result["ma_200_note"] = "Historical data unavailable"

    iv_data = _fetch_atm_iv(ticker, underlying_price=price_data.get("price"))
    if iv_data:
        result["implied_volatility"] = iv_data["implied_volatility"]
        result["iv_source"] = iv_data["source"]
        result["iv_strike"] = iv_data["strike"]
        result["iv_delta"] = iv_data["delta"]
        result["iv_is_atm"] = iv_data["is_atm"]
    else:
        result["implied_volatility"] = None
        result["iv_note"] = "Options data unavailable"

    return result


def fetch_quote(ticker: str) -> Optional[Dict]:
    """
    Simple price quote for quick checks.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with price and basic data, or None if fetch fails
    """
    return fetch_price(ticker)


def fetch_options_data(ticker: str, strike: float, expiration: str) -> Optional[Dict]:
    """
    Fetch options chain data for monitor skill.

    Data fetched:
    - Current option bid/ask/mid price
    - Greeks (delta, theta, gamma, vega)
    - Implied volatility
    - Open interest
    - Volume

    IMPORTANT: Includes data quality validation with circuit breaker.
    Will halt trading after 3 consecutive validation failures.

    Args:
        ticker: Stock ticker symbol (underlying)
        strike: Strike price
        expiration: Expiration date (YYYY-MM-DD format)

    Returns:
        Dict with options data, or None if fetch/validation fails
    """
    ticker = ticker.upper()
    monitor = get_monitor()

    # Check if circuit breaker is active
    if monitor.is_circuit_breaker_active():
        raise RuntimeError("⛔ Circuit breaker is active. Options trading halted. Reset manually after reviewing data quality logs.")

    try:
        script_path = Path(__file__).parent / "ibkr_paper.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "quote_option",
                ticker,
                "--strike", str(strike),
                "--expiration", expiration,
                "--right", "CALL"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = f"IBKR fetch failed: {result.stderr}"
            print(f"Options fetch failed for {ticker}: {error_msg}", file=sys.stderr)
            monitor.record_failure("ibkr_connection", error_msg, ticker)
            return None

        data = json.loads(result.stdout)

        if "error" in data or not data.get("mid_price"):
            error_msg = f"IBKR returned error or missing mid_price"
            monitor.record_failure("ibkr_response", error_msg, ticker)
            return None

        # ===== DATA QUALITY VALIDATION =====

        # 1. Validate Greeks
        greeks = {
            "delta": data.get("delta"),
            "theta": data.get("theta"),
            "gamma": data.get("gamma"),
            "vega": data.get("vega"),
            "implied_volatility": data.get("implied_volatility")
        }

        valid, error = monitor.validate_greeks(greeks, right="CALL")
        if not valid:
            print(f"⚠️  Greeks validation failed for {ticker}: {error}", file=sys.stderr)
            monitor.record_failure("greeks_validation", error, ticker)
            return None

        # 2. Validate Pricing
        valid, error = monitor.validate_pricing(
            data.get("bid"),
            data.get("ask"),
            data.get("last")
        )
        if not valid:
            print(f"⚠️  Pricing validation failed for {ticker}: {error}", file=sys.stderr)
            monitor.record_failure("pricing_validation", error, ticker)
            return None

        # 3. Validate Liquidity (warning only - doesn't trigger circuit breaker)
        valid, warning = monitor.validate_liquidity(
            data.get("open_interest"),
            data.get("volume")
        )
        if not valid:
            # Liquidity warnings are logged but don't fail the request
            print(f"⚠️  Liquidity warning for {ticker}: {warning}", file=sys.stderr)
            # Don't return None - just warn

        # All validations passed - reset failure counter
        monitor.reset_failures()

        return {
            "ticker": ticker,
            "strike": strike,
            "expiration": expiration,
            "right": "CALL",
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "last": data.get("last"),
            "mid_price": data.get("mid_price"),
            "delta": data.get("delta"),
            "theta": data.get("theta"),
            "gamma": data.get("gamma"),
            "vega": data.get("vega"),
            "implied_volatility": data.get("implied_volatility"),
            "open_interest": data.get("open_interest"),
            "volume": data.get("volume"),
            "timestamp": datetime.now().isoformat(),
            "source": data.get("source", "IBKR Paper"),
            "data_quality_validated": True  # Flag that validation passed
        }

    except subprocess.TimeoutExpired:
        error_msg = f"IBKR timeout after 30 seconds"
        print(f"Options fetch timeout for {ticker}", file=sys.stderr)
        monitor.record_failure("ibkr_timeout", error_msg, ticker)
        return None
    except json.JSONDecodeError as e:
        error_msg = f"IBKR JSON parse error: {e}"
        print(f"Options JSON parse error for {ticker}: {error_msg}", file=sys.stderr)
        monitor.record_failure("ibkr_json_error", error_msg, ticker)
        return None
    except RuntimeError as e:
        # Circuit breaker triggered - re-raise to halt execution
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"Options fetch error for {ticker}: {error_msg}", file=sys.stderr)
        monitor.record_failure("unexpected_error", error_msg, ticker)
        return None


def main():
    """CLI interface for data fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch trading data from multiple sources")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # fetch_all command
    parser_all = subparsers.add_parser("fetch_all", help="Fetch all data for analyze skill")
    parser_all.add_argument("ticker", help="Stock ticker symbol")
    parser_all.add_argument("--industry", default="general",
                           help="Industry for Z-Score adjustment")
    parser_all.add_argument("--archetype", default="general",
                           help="Trade archetype (pdufa, merger_arb, activist, etc.)")

    # fetch_market_data command
    parser_market = subparsers.add_parser("fetch_market_data",
                                          help="Fetch market data for score/monitor skills")
    parser_market.add_argument("ticker", help="Stock ticker symbol")

    # fetch_quote command
    parser_quote = subparsers.add_parser("fetch_quote", help="Fetch simple price quote")
    parser_quote.add_argument("ticker", help="Stock ticker symbol")

    # fetch_options_data command
    parser_options = subparsers.add_parser("fetch_options_data",
                                           help="Fetch options data for monitor skill")
    parser_options.add_argument("ticker", help="Stock ticker symbol (underlying)")
    parser_options.add_argument("--strike", type=float, required=True, help="Strike price")
    parser_options.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "fetch_all":
        data = fetch_all(args.ticker, args.industry, args.archetype)
        print(json.dumps(data, indent=2))

        # Exit with error code if kill screens failed
        if data["kill_screens_status"] == "FAIL":
            sys.exit(1)

    elif args.command == "fetch_market_data":
        data = fetch_market_data(args.ticker)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print(f"ERROR: Could not fetch market data for {args.ticker}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "fetch_quote":
        data = fetch_quote(args.ticker)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print(f"ERROR: Could not fetch quote for {args.ticker}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "fetch_options_data":
        data = fetch_options_data(args.ticker, args.strike, args.expiration)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print(f"ERROR: Could not fetch options data for {args.ticker}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
