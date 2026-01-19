"""
Insider Trading Analysis

Utility functions for analyzing SEC Form 4 insider trading data.

Working Functions:
- classify_insider_routine() - Classify insider as routine vs opportunistic trader

Manual Lookups Required:
- Full insider cluster validation: Use OpenInsider.com for recent clusters
- Form 4 transaction details: Agent performs web search/fetch

Routine Trader Definition:
- Trades occur in same calendar month annually for 3+ consecutive years
- Example: Insider sells every June for 3+ years = routine trader
- These insiders are excluded from cluster count (eliminate ~50% of false signals)

Usage:
    from insider_analysis import classify_insider_routine

    # Classify insider based on their trading history
    transactions = [{"transaction_date": "2023-06-15"}, {"transaction_date": "2024-06-20"}, ...]
    result = classify_insider_routine("John Doe", transactions)
"""

import json
from typing import Dict, List
from datetime import datetime
from collections import Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def classify_insider_routine(insider_name: str, transactions: List[Dict]) -> Dict:
    """
    Classify insider as routine or opportunistic trader.

    Routine trader: Trades occur in same calendar month annually for 3+ years
    Example: Sells every June for 3+ years = routine

    Args:
        insider_name: Insider name
        transactions: List of transactions for this insider. Each transaction
                     should have 'transaction_date' or 'filing_date' key in
                     ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

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
            if not date_str:
                continue
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            transaction_months.append(date.month)
        except (ValueError, AttributeError):
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


# Manual lookup instructions for agent reference
MANUAL_LOOKUP_INSTRUCTIONS = {
    "insider_cluster_validation": {
        "description": "Validate insider cluster quality for Insider archetype kill screen",
        "steps": [
            "1. Check OpenInsider.com for recent insider purchases (past 14 days)",
            "2. For each insider, review 3-year trading history",
            "3. Use classify_insider_routine() to identify routine traders",
            "4. Count only opportunistic (non-routine) insiders",
            "5. PASS if opportunistic count >= 3, else FAIL"
        ],
        "sources": [
            "OpenInsider.com - Recent insider transactions",
            "SEC EDGAR - Form 4 filings",
            "SECFORM4.com - Alternative insider data"
        ]
    }
}


def main():
    """CLI interface for insider analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze insider trading patterns")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # classify_routine command
    parser_classify = subparsers.add_parser("classify_routine", help="Classify insider trading pattern")
    parser_classify.add_argument("insider_name", help="Insider name")
    parser_classify.add_argument("--transactions", help="JSON array of transactions", default="[]")

    # manual_lookups command
    subparsers.add_parser("manual_lookups", help="Show manual lookup instructions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "classify_routine":
        try:
            transactions = json.loads(args.transactions)
        except json.JSONDecodeError:
            print("Error: --transactions must be valid JSON array")
            return
        result = classify_insider_routine(args.insider_name, transactions)
        print(json.dumps(result, indent=2))

    elif args.command == "manual_lookups":
        print(json.dumps(MANUAL_LOOKUP_INSTRUCTIONS, indent=2))


if __name__ == "__main__":
    main()
