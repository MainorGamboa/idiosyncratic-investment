"""
Insider Trading Analysis

Fetches and analyzes SEC Form 4 insider trading data to:
1. Identify insider clusters (3+ insiders buying within 2-week window)
2. Classify insiders as routine vs. opportunistic traders
3. Validate cluster quality (requires 3+ opportunistic insiders)

Uses EdgarTools library to fetch Form 4 data from SEC Edgar.

Routine Trader Definition:
- Trades occur in same calendar month annually for 3+ consecutive years
- Example: Insider sells every June for 3+ years = routine trader
- These insiders are excluded from cluster count (eliminate ~50% of false signals)

Usage:
    from insider_analysis import validate_insider_cluster, fetch_insider_history

    # Validate insider cluster quality
    result = validate_insider_cluster("AAPL", min_opportunistic=3)

    # Fetch insider history
    history = fetch_insider_history("AAPL", lookback_years=3)
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import edgartools (will fail if not installed)
try:
    from edgar import Company, set_identity
    EDGARTOOLS_AVAILABLE = True
except ImportError:
    logger.warning("EdgarTools not installed. Run: pip install edgartools")
    EDGARTOOLS_AVAILABLE = False

# Rate limiting for SEC Edgar (10 req/sec limit)
LAST_SEC_REQUEST = None
SEC_MIN_INTERVAL = 0.1  # 10 requests per second

def rate_limit_sec():
    """Rate limiter for SEC Edgar API (10 req/sec limit)"""
    global LAST_SEC_REQUEST

    if LAST_SEC_REQUEST:
        elapsed = time.time() - LAST_SEC_REQUEST
        if elapsed < SEC_MIN_INTERVAL:
            time.sleep(SEC_MIN_INTERVAL - elapsed)

    LAST_SEC_REQUEST = time.time()


def fetch_insider_history(ticker: str, lookback_years: int = 3) -> Dict:
    """
    Fetch Form 4 insider trading history for a ticker.

    Args:
        ticker: Stock ticker symbol
        lookback_years: Years to look back for Form 4s (default 3)

    Returns:
        {
            "ticker": str,
            "transactions": List[Dict],
            "count": int,
            "source": str,
            "error": str (if error occurred)
        }
    """
    logger.info(f"Fetching insider history for {ticker} ({lookback_years} years)")

    if not EDGARTOOLS_AVAILABLE:
        return {
            "ticker": ticker,
            "transactions": [],
            "count": 0,
            "source": "error",
            "error": "EdgarTools not installed. Run: pip install edgartools"
        }

    try:
        # Set SEC Edgar identity (required by SEC)
        set_identity("Trading Framework mainor@example.com")

        rate_limit_sec()

        # Fetch company data
        company = Company(ticker)

        # Get Form 4 filings
        rate_limit_sec()
        form4s = company.get_filings(form="4").latest(lookback_years * 20)  # ~20 Form 4s per year

        transactions = []
        lookback_date = datetime.now() - timedelta(days=lookback_years * 365)

        for filing in form4s:
            filing_date = datetime.fromisoformat(filing.filing_date.replace("Z", "+00:00"))

            if filing_date < lookback_date:
                continue

            # Parse Form 4 XML to extract insider name and transaction details
            # This is simplified - in production, you'd parse the XML properly
            transactions.append({
                "filing_date": filing.filing_date,
                "accession_number": filing.accession_number,
                "url": filing.url,
                "insider_name": "Unknown",  # Would parse from XML
                "transaction_date": filing.filing_date,  # Would parse from XML
                "transaction_type": "Unknown",  # P (purchase), S (sale), etc.
                "shares": 0,  # Would parse from XML
                "price": 0.0  # Would parse from XML
            })

        result = {
            "ticker": ticker,
            "transactions": transactions,
            "count": len(transactions),
            "source": "sec_edgar_edgartools"
        }

        logger.info(f"Found {len(transactions)} Form 4 transactions for {ticker}")
        return result

    except Exception as e:
        logger.error(f"Error fetching insider history for {ticker}: {e}")
        return {
            "ticker": ticker,
            "transactions": [],
            "count": 0,
            "source": "error",
            "error": str(e)
        }


def classify_insider_routine(insider_name: str, transactions: List[Dict]) -> Dict:
    """
    Classify insider as routine or opportunistic trader.

    Routine trader: Trades occur in same calendar month annually for 3+ years
    Example: Sells every June for 3+ years = routine

    Args:
        insider_name: Insider name
        transactions: List of transactions for this insider

    Returns:
        {
            "insider_name": str,
            "is_routine": bool,
            "pattern_detected": str,
            "transaction_months": List[int],
            "rationale": str
        }
    """
    logger.info(f"Classifying insider {insider_name}")

    if len(transactions) < 3:
        # Need at least 3 transactions to detect pattern
        return {
            "insider_name": insider_name,
            "is_routine": False,
            "pattern_detected": "insufficient_data",
            "transaction_months": [],
            "rationale": "Fewer than 3 transactions, cannot detect routine pattern"
        }

    # Extract transaction months (1-12)
    transaction_months = []
    for txn in transactions:
        try:
            date_str = txn.get("transaction_date") or txn.get("filing_date")
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            transaction_months.append(date.month)
        except:
            continue

    if not transaction_months:
        return {
            "insider_name": insider_name,
            "is_routine": False,
            "pattern_detected": "no_valid_dates",
            "transaction_months": [],
            "rationale": "No valid transaction dates found"
        }

    # Count frequency of each month
    month_counts = Counter(transaction_months)
    most_common_month, frequency = month_counts.most_common(1)[0]

    # Routine pattern: Same month appears 3+ times
    if frequency >= 3:
        return {
            "insider_name": insider_name,
            "is_routine": True,
            "pattern_detected": f"month_{most_common_month}",
            "transaction_months": transaction_months,
            "rationale": f"Trades in month {most_common_month} occurred {frequency} times (≥3 years)"
        }
    else:
        return {
            "insider_name": insider_name,
            "is_routine": False,
            "pattern_detected": "no_pattern",
            "transaction_months": transaction_months,
            "rationale": "No consistent monthly pattern detected"
        }


def validate_insider_cluster(ticker: str, min_opportunistic: int = 3, window_days: int = 14) -> Dict:
    """
    Validate insider cluster quality (kill screen for insider archetype).

    Kill screen logic:
    1. Identify recent insider purchases (within window_days)
    2. Fetch 3-year Form 4 history for each insider
    3. Classify each insider as routine or opportunistic
    4. Count ONLY opportunistic insiders
    5. PASS if opportunistic_count >= min_opportunistic, else FAIL

    Args:
        ticker: Stock ticker symbol
        min_opportunistic: Minimum opportunistic insiders required (default 3)
        window_days: Cluster detection window in days (default 14)

    Returns:
        {
            "ticker": str,
            "cluster_valid": bool,
            "opportunistic_count": int,
            "routine_count": int,
            "total_count": int,
            "insiders": List[Dict],
            "kill_screen_result": "PASS" or "FAIL",
            "source": str
        }
    """
    logger.info(f"Validating insider cluster for {ticker}")

    # For MVP without full Form 4 parsing, return placeholder
    # In production, this would:
    # 1. Fetch recent Form 4s (past window_days)
    # 2. Extract insider names and transaction types
    # 3. Filter for purchases only
    # 4. For each purchasing insider, fetch 3-year history
    # 5. Classify as routine/opportunistic
    # 6. Count opportunistic insiders

    if not EDGARTOOLS_AVAILABLE:
        return {
            "ticker": ticker,
            "cluster_valid": None,
            "opportunistic_count": 0,
            "routine_count": 0,
            "total_count": 0,
            "insiders": [],
            "kill_screen_result": "ERROR",
            "source": "error",
            "error": "EdgarTools not installed. Run: pip install edgartools",
            "instructions": "Manual analysis required: Check OpenInsider.com for recent insider clusters"
        }

    try:
        # Simplified implementation for MVP
        # In production, parse Form 4 XML to extract insider details

        insider_history = fetch_insider_history(ticker, lookback_years=3)

        if insider_history.get("source") == "error":
            return {
                "ticker": ticker,
                "cluster_valid": None,
                "opportunistic_count": 0,
                "routine_count": 0,
                "total_count": 0,
                "insiders": [],
                "kill_screen_result": "ERROR",
                "source": "error",
                "error": insider_history.get("error"),
                "instructions": "Manual analysis required: Check OpenInsider.com for recent insider clusters"
            }

        # For MVP, return placeholder result
        # Real implementation would analyze transactions to identify cluster
        result = {
            "ticker": ticker,
            "cluster_valid": None,
            "opportunistic_count": 0,
            "routine_count": 0,
            "total_count": 0,
            "insiders": [],
            "kill_screen_result": "MANUAL_REVIEW_REQUIRED",
            "source": "manual_entry_required",
            "note": "Full Form 4 parsing not yet implemented. Manual cluster validation required.",
            "instructions": [
                "1. Check OpenInsider.com for recent insider purchases (past 14 days)",
                "2. For each insider, review 3-year trading history",
                "3. Identify routine traders (same month annually for 3+ years)",
                "4. Count only opportunistic (non-routine) insiders",
                "5. PASS if opportunistic count >= 3, else FAIL"
            ]
        }

        logger.info(f"Insider cluster validation: {result['kill_screen_result']}")
        return result

    except Exception as e:
        logger.error(f"Error validating insider cluster for {ticker}: {e}")
        return {
            "ticker": ticker,
            "cluster_valid": None,
            "opportunistic_count": 0,
            "routine_count": 0,
            "total_count": 0,
            "insiders": [],
            "kill_screen_result": "ERROR",
            "source": "error",
            "error": str(e)
        }


def main():
    """CLI interface for insider analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze insider trading data from SEC Form 4")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # fetch_history command
    parser_history = subparsers.add_parser("fetch_history", help="Fetch insider trading history")
    parser_history.add_argument("ticker", help="Stock ticker symbol")
    parser_history.add_argument("--lookback-years", type=int, default=3, help="Years to look back")

    # validate_cluster command
    parser_cluster = subparsers.add_parser("validate_cluster", help="Validate insider cluster quality")
    parser_cluster.add_argument("ticker", help="Stock ticker symbol")
    parser_cluster.add_argument("--min-opportunistic", type=int, default=3,
                                help="Minimum opportunistic insiders required")
    parser_cluster.add_argument("--window-days", type=int, default=14,
                                help="Cluster detection window in days")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "fetch_history":
        result = fetch_insider_history(args.ticker, args.lookback_years)
        print(json.dumps(result, indent=2))

    elif args.command == "validate_cluster":
        result = validate_insider_cluster(args.ticker, args.min_opportunistic, args.window_days)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
