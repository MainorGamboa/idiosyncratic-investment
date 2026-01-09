"""
Data Fetcher Module

Main interface for fetching all data needed by trading skills.
Aggregates data from multiple sources:
- Price data (IBKR, Stooq, Yahoo)
- Financial data (SEC API)
- Market data (200-day MA, volume, IV)

Used by analyze, score, and monitor skills.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Import local modules
from price_sources import fetch_price, get_bid_ask_midpoint
from sec_api import (
    parse_financials,
    fetch_two_periods,
    calculate_m_score,
    calculate_z_score,
    get_cik_from_ticker
)

# Import new v1.1 modules for archetype-specific data
try:
    from regulatory_data import check_form_483, check_ema_approval, classify_crl
    REGULATORY_DATA_AVAILABLE = True
except ImportError:
    REGULATORY_DATA_AVAILABLE = False

try:
    from insider_analysis import validate_insider_cluster
    INSIDER_ANALYSIS_AVAILABLE = True
except ImportError:
    INSIDER_ANALYSIS_AVAILABLE = False

try:
    from warn_act_checker import check_warn_filing, check_warn_for_activist_exit, check_warn_for_spinoff_sizing
    WARN_ACT_AVAILABLE = True
except ImportError:
    WARN_ACT_AVAILABLE = False


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

    # 3. Archetype-specific data (v1.1 enhancements)
    archetype_lower = archetype.lower()

    if archetype_lower == "pdufa" and REGULATORY_DATA_AVAILABLE:
        # PDUFA: Check Form 483 with OAI and EMA approval
        try:
            # Note: company_name would need to be passed or looked up
            # For now, use ticker as placeholder
            company_name = ticker  # TODO: Improve company name lookup

            form_483 = check_form_483(company_name)
            result["form_483_with_oai"] = form_483.get("has_oai", None)
            result["form_483_details"] = form_483
            result["data_sources_used"].append("regulatory_data")

            # EMA approval check would need drug name
            # For MVP, include placeholder
            result["ema_approved"] = None
            result["ema_note"] = "Drug name required for EMA approval check"
        except Exception as e:
            result["errors"].append(f"Error fetching PDUFA regulatory data: {e}")

    elif archetype_lower == "insider" and INSIDER_ANALYSIS_AVAILABLE:
        # Insider: Validate cluster quality (kill screen)
        try:
            cluster = validate_insider_cluster(ticker, min_opportunistic=3)
            result["insider_cluster_valid"] = cluster.get("cluster_valid")
            result["opportunistic_count"] = cluster.get("opportunistic_count", 0)
            result["routine_count"] = cluster.get("routine_count", 0)
            result["insider_cluster_details"] = cluster
            result["data_sources_used"].append("insider_analysis")

            # Update kill screens status if cluster invalid
            if cluster.get("cluster_valid") == False:
                result["kill_screens_status"] = "FAIL"
                result["kill_screen_failed"] = "insider_cluster_quality"
        except Exception as e:
            result["errors"].append(f"Error validating insider cluster: {e}")

    elif archetype_lower in ["activist", "spinoff"] and WARN_ACT_AVAILABLE:
        # Activist/Spin-off: Check WARN filings
        try:
            company_name = ticker  # TODO: Improve company name lookup
            warn = check_warn_filing(company_name)
            result["has_warn_filing"] = warn.get("has_warn", None)
            result["warn_details"] = warn
            result["data_sources_used"].append("warn_act_checker")
        except Exception as e:
            result["errors"].append(f"Error checking WARN filings: {e}")

    elif archetype_lower == "merger_arb":
        # Merger Arb: Note for second request, CFIUS, China-connected checks
        # These would be detected during scoring phase, not kill screens
        result["merger_arb_note"] = "Check for second request, CFIUS exposure, and China-connected buyer during scoring"

    # 4. Summary
    kill_screens_passed = result.get("financial_screens_pass", False)

    # Override if insider cluster failed
    if result.get("kill_screen_failed"):
        kill_screens_passed = False

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

    # TODO: 200-day MA calculation (requires historical data)
    # For MVP, return placeholder
    result["ma_200"] = None
    result["ma_200_note"] = "Historical data not implemented yet"

    # TODO: IV calculation (requires options data)
    # For MVP, return placeholder
    result["implied_volatility"] = None
    result["iv_note"] = "Options data not implemented yet"

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


if __name__ == "__main__":
    main()
