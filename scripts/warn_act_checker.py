"""
WARN Act Filing Checker

Checks state WARN (Worker Adjustment and Retraining Notification) Act databases
for layoff announcements. Used for:

1. Activist archetype: WARN filing with "loss of contract" = exit signal
2. Spin-off archetype: WARN filing at SpinCo = reduce position size 50%

WARN Act requires employers with 100+ employees to provide 60-day notice
of plant closings or mass layoffs.

State Databases:
- California: https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN
- New York: https://dol.ny.gov/warn-notices
- Many states publish WARN notices online (varies by state)

Usage:
    from warn_act_checker import check_warn_filing, analyze_warn_language

    # Check for WARN filing
    result = check_warn_filing("Sears Holdings", state="CA")

    # Analyze WARN filing text
    analysis = analyze_warn_language("Closure due to loss of major contract with...")
"""

import requests
import json
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
import re

# Try to import BeautifulSoup for web scraping
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    logging.warning("BeautifulSoup not installed. Run: pip install beautifulsoup4")
    BS4_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_warn_filing(company_name: str, state: Optional[str] = None, lookback_days: int = 180) -> Dict:
    """
    Check for WARN Act filings for a company.

    Args:
        company_name: Company name (e.g., "Sears Holdings")
        state: State code (e.g., "CA", "NY") or None to search all
        lookback_days: Days to look back for WARN filings (default 180)

    Returns:
        {
            "has_warn": bool,
            "filings": List[Dict],
            "filing_count": int,
            "most_recent_date": str,
            "source": str
        }
    """
    logger.info(f"Checking WARN filings for {company_name} (state={state})")

    # For MVP without web scraping implementation, return placeholder
    # In production, this would scrape state WARN databases

    result = {
        "has_warn": None,
        "filings": [],
        "filing_count": 0,
        "most_recent_date": None,
        "source": "manual_entry_required",
        "instructions": f"Manual WARN Act check required for {company_name}",
        "databases": {
            "california": "https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN",
            "new_york": "https://dol.ny.gov/warn-notices",
            "texas": "https://www.twc.texas.gov/businesses/worker-adjustment-retraining-notification-warn-notices",
            "national_search": "Search '[company name] WARN Act notice' in Google"
        }
    }

    logger.info(f"WARN filing check: {result}")
    return result


def analyze_warn_language(warn_text: str) -> Dict:
    """
    Analyze WARN filing text for "loss of contract" or similar language.

    Keywords indicating contract loss:
    - "loss of contract"
    - "contract termination"
    - "customer loss"
    - "loss of business"
    - "contract not renewed"

    Args:
        warn_text: Text of WARN filing (reason for layoff)

    Returns:
        {
            "loss_of_contract": bool,
            "keywords_found": List[str],
            "rationale": str
        }
    """
    logger.info(f"Analyzing WARN filing language")

    if not warn_text:
        return {
            "loss_of_contract": False,
            "keywords_found": [],
            "rationale": "No WARN text provided"
        }

    # Keywords indicating contract loss
    contract_loss_keywords = [
        r"loss\s+of\s+contract",
        r"contract\s+termination",
        r"customer\s+loss",
        r"loss\s+of\s+business",
        r"contract\s+not\s+renewed",
        r"lost\s+contract",
        r"contract\s+canceled",
        r"contract\s+cancellation"
    ]

    warn_text_lower = warn_text.lower()
    keywords_found = []

    for keyword_pattern in contract_loss_keywords:
        if re.search(keyword_pattern, warn_text_lower):
            keywords_found.append(keyword_pattern.replace(r"\s+", " "))

    loss_of_contract = len(keywords_found) > 0

    result = {
        "loss_of_contract": loss_of_contract,
        "keywords_found": keywords_found,
        "rationale": f"Found {len(keywords_found)} contract loss indicators" if loss_of_contract else "No contract loss language detected"
    }

    logger.info(f"WARN language analysis: {result}")
    return result


def search_california_warn(company_name: str, lookback_days: int = 180) -> Dict:
    """
    Search California EDD WARN database for company.

    California has one of the best-maintained WARN databases.

    Args:
        company_name: Company name
        lookback_days: Days to look back

    Returns:
        {
            "filings": List[Dict],
            "count": int,
            "source": str
        }
    """
    logger.info(f"Searching California WARN database for {company_name}")

    if not BS4_AVAILABLE:
        return {
            "filings": [],
            "count": 0,
            "source": "error",
            "error": "BeautifulSoup not installed. Run: pip install beautifulsoup4"
        }

    try:
        # California EDD WARN database
        # Note: This is a placeholder - actual implementation would scrape the EDD website
        # The EDD site structure changes frequently, so robust scraping is complex

        url = "https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN"

        # For MVP, return placeholder
        result = {
            "filings": [],
            "count": 0,
            "source": "manual_entry_required",
            "instructions": f"Visit {url} and search for {company_name}",
            "note": "California EDD WARN database requires web scraping. Manual check recommended."
        }

        logger.info(f"California WARN search: {result}")
        return result

    except Exception as e:
        logger.error(f"Error searching California WARN: {e}")
        return {
            "filings": [],
            "count": 0,
            "source": "error",
            "error": str(e)
        }


def check_warn_for_activist_exit(company_name: str, state: Optional[str] = None) -> Dict:
    """
    Check WARN filings for activist archetype exit trigger.

    Exit trigger: WARN filing with "loss of contract" language

    Args:
        company_name: Company name
        state: State code or None

    Returns:
        {
            "exit_triggered": bool,
            "rationale": str,
            "filings": List[Dict],
            "source": str
        }
    """
    logger.info(f"Checking WARN exit trigger for activist on {company_name}")

    warn_result = check_warn_filing(company_name, state)

    if warn_result.get("source") == "manual_entry_required":
        return {
            "exit_triggered": None,
            "rationale": "Manual WARN check required",
            "filings": [],
            "source": "manual_entry_required",
            "instructions": warn_result.get("instructions")
        }

    # Analyze each filing for contract loss language
    exit_triggered = False
    for filing in warn_result.get("filings", []):
        reason = filing.get("reason", "")
        analysis = analyze_warn_language(reason)

        if analysis["loss_of_contract"]:
            exit_triggered = True
            break

    result = {
        "exit_triggered": exit_triggered,
        "rationale": "WARN filing with contract loss language detected" if exit_triggered else "No contract loss WARN filings found",
        "filings": warn_result.get("filings", []),
        "source": warn_result.get("source")
    }

    logger.info(f"Activist WARN exit trigger: {result}")
    return result


def check_warn_for_spinoff_sizing(spinco_name: str, parent_name: str, state: Optional[str] = None) -> Dict:
    """
    Check WARN filings for spin-off position sizing adjustment.

    Position sizing: WARN filing at SpinCo = reduce size 50%

    Args:
        spinco_name: Spin-off company name
        parent_name: Parent company name
        state: State code or None

    Returns:
        {
            "size_down_50pct": bool,
            "rationale": str,
            "filings": List[Dict],
            "source": str
        }
    """
    logger.info(f"Checking WARN for spin-off sizing: SpinCo={spinco_name}, Parent={parent_name}")

    # Check both SpinCo and parent for WARN filings
    spinco_warn = check_warn_filing(spinco_name, state)
    parent_warn = check_warn_filing(parent_name, state)

    if spinco_warn.get("source") == "manual_entry_required":
        return {
            "size_down_50pct": None,
            "rationale": "Manual WARN check required",
            "filings": [],
            "source": "manual_entry_required",
            "instructions": spinco_warn.get("instructions")
        }

    # If SpinCo has WARN filing, reduce position size
    size_down = spinco_warn.get("filing_count", 0) > 0

    result = {
        "size_down_50pct": size_down,
        "rationale": f"WARN filing detected at SpinCo ({spinco_name}), reduce position 50%" if size_down else "No WARN filings at SpinCo",
        "filings": {
            "spinco": spinco_warn.get("filings", []),
            "parent": parent_warn.get("filings", [])
        },
        "source": spinco_warn.get("source")
    }

    logger.info(f"Spin-off WARN sizing: {result}")
    return result


def main():
    """CLI interface for WARN Act checking."""
    import argparse

    parser = argparse.ArgumentParser(description="Check WARN Act filings")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # check_warn command
    parser_warn = subparsers.add_parser("check_warn", help="Check for WARN filings")
    parser_warn.add_argument("company_name", help="Company name")
    parser_warn.add_argument("--state", help="State code (e.g., CA, NY)")
    parser_warn.add_argument("--lookback-days", type=int, default=180, help="Days to look back")

    # analyze_language command
    parser_language = subparsers.add_parser("analyze_language", help="Analyze WARN filing text")
    parser_language.add_argument("warn_text", help="WARN filing text")

    # activist_exit command
    parser_activist = subparsers.add_parser("activist_exit", help="Check activist exit trigger")
    parser_activist.add_argument("company_name", help="Company name")
    parser_activist.add_argument("--state", help="State code")

    # spinoff_sizing command
    parser_spinoff = subparsers.add_parser("spinoff_sizing", help="Check spin-off position sizing")
    parser_spinoff.add_argument("spinco_name", help="Spin-off company name")
    parser_spinoff.add_argument("parent_name", help="Parent company name")
    parser_spinoff.add_argument("--state", help="State code")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "check_warn":
        result = check_warn_filing(args.company_name, args.state, args.lookback_days)
        print(json.dumps(result, indent=2))

    elif args.command == "analyze_language":
        result = analyze_warn_language(args.warn_text)
        print(json.dumps(result, indent=2))

    elif args.command == "activist_exit":
        result = check_warn_for_activist_exit(args.company_name, args.state)
        print(json.dumps(result, indent=2))

    elif args.command == "spinoff_sizing":
        result = check_warn_for_spinoff_sizing(args.spinco_name, args.parent_name, args.state)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
