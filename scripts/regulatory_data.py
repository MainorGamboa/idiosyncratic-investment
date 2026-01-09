"""
Regulatory Data Fetcher

Fetches FDA regulatory data for PDUFA archetype analysis:
- Form 483 inspections with OAI (Official Action Indicated) status
- EMA (European Medicines Agency) approval decisions
- CRL (Complete Response Letter) classifications

Data Sources:
- openFDA API (free, public, no auth required)
- EMA medicines database
- FDA FOIA Reading Room (fallback)

Usage:
    from regulatory_data import check_form_483, check_ema_approval, classify_crl

    # Check for Form 483 with OAI
    form_483 = check_form_483("Sarepta Therapeutics")

    # Check EMA approval
    ema = check_ema_approval("eteplirsen")

    # Classify CRL
    crl = classify_crl("SRPT", "eteplirsen")
"""

import requests
import json
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
LAST_REQUEST_TIME = {}

def rate_limit(api_name: str, min_interval_seconds: float = 0.25):
    """Rate limiter for API calls (respects 240 req/min for openFDA, 10 req/sec for SEC)"""
    global LAST_REQUEST_TIME

    if api_name in LAST_REQUEST_TIME:
        elapsed = time.time() - LAST_REQUEST_TIME[api_name]
        if elapsed < min_interval_seconds:
            time.sleep(min_interval_seconds - elapsed)

    LAST_REQUEST_TIME[api_name] = time.time()


def check_form_483(company_name: str, lookback_years: int = 3) -> Dict:
    """
    Check for FDA Form 483 inspections with OAI (Official Action Indicated) status.

    Form 483s are observations noted during FDA inspections. OAI status indicates
    significant violations requiring official action before approval.

    Args:
        company_name: Company name (e.g., "Sarepta Therapeutics")
        lookback_years: Years to look back for Form 483s (default 3)

    Returns:
        {
            "has_483": bool,
            "has_oai": bool,
            "details": str,
            "inspections": List[Dict],
            "source": str
        }
    """
    logger.info(f"Checking Form 483 for {company_name}")

    try:
        # openFDA doesn't have Form 483 data in structured API
        # This is a placeholder for web scraping FDA FOIA Reading Room
        # In production, you'd scrape: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations

        # For MVP, return placeholder with manual entry instructions
        result = {
            "has_483": None,
            "has_oai": None,
            "details": f"Form 483 check requires manual verification. Search FDA FOIA Reading Room for {company_name}",
            "inspections": [],
            "source": "manual_entry_required",
            "instructions": "Visit https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/fda-warning-letters and search for company name"
        }

        logger.info(f"Form 483 check result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking Form 483 for {company_name}: {e}")
        return {
            "has_483": None,
            "has_oai": None,
            "details": f"Error: {str(e)}",
            "inspections": [],
            "source": "error"
        }


def check_ema_approval(drug_name: str) -> Dict:
    """
    Check if drug has EMA (European Medicines Agency) approval.

    91-98% EMA→FDA concordance provides strong signal for FDA approval.

    Args:
        drug_name: Drug name (e.g., "eteplirsen")

    Returns:
        {
            "ema_approved": bool,
            "approval_date": str,
            "decision_url": str,
            "details": str,
            "source": str
        }
    """
    logger.info(f"Checking EMA approval for {drug_name}")

    try:
        # EMA doesn't have a public API for medicine approvals
        # This is a placeholder for web scraping EMA medicines database
        # In production, you'd scrape: https://www.ema.europa.eu/en/medicines

        # For MVP, return placeholder with manual entry instructions
        result = {
            "ema_approved": None,
            "approval_date": None,
            "decision_url": None,
            "details": f"EMA approval check requires manual verification. Search EMA medicines database for {drug_name}",
            "source": "manual_entry_required",
            "instructions": "Visit https://www.ema.europa.eu/en/medicines and search for drug name"
        }

        logger.info(f"EMA approval check result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking EMA approval for {drug_name}: {e}")
        return {
            "ema_approved": None,
            "approval_date": None,
            "decision_url": None,
            "details": f"Error: {str(e)}",
            "source": "error"
        }


def classify_crl(ticker: str, drug_name: str) -> Dict:
    """
    Classify CRL (Complete Response Letter) as Class 1 or Class 2.

    Class 1: Manufacturing/labeling issues (2-month timeline)
    Class 2: Efficacy/safety issues requiring additional studies (6-month timeline)

    Args:
        ticker: Stock ticker (e.g., "SRPT")
        drug_name: Drug name (e.g., "eteplirsen")

    Returns:
        {
            "crl_class": str ("class_1", "class_2", or None),
            "timeline_months": int,
            "rationale": str,
            "details": str,
            "source": str
        }
    """
    logger.info(f"Classifying CRL for {ticker} ({drug_name})")

    try:
        # openFDA doesn't have CRL classification data
        # This requires reading CRL letters from FDA FOIA requests
        # In production, you'd analyze CRL text for:
        # - Manufacturing/CMC issues → Class 1
        # - Clinical/efficacy issues → Class 2

        # For MVP, return placeholder with manual entry instructions
        result = {
            "crl_class": None,
            "timeline_months": None,
            "rationale": f"CRL classification requires manual analysis of CRL letter for {drug_name}",
            "details": "Class 1 (manufacturing/labeling) = 2 months, Class 2 (efficacy/safety) = 6 months",
            "source": "manual_entry_required",
            "instructions": "Request CRL letter via FDA FOIA or check company's SEC filings (8-K) for CRL details"
        }

        logger.info(f"CRL classification result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error classifying CRL for {ticker} ({drug_name}): {e}")
        return {
            "crl_class": None,
            "timeline_months": None,
            "rationale": f"Error: {str(e)}",
            "details": "",
            "source": "error"
        }


def search_fda_enforcement(company_name: str, limit: int = 10) -> Dict:
    """
    Search FDA drug enforcement reports for company.

    Uses openFDA API to find warning letters, recalls, etc.

    Args:
        company_name: Company name
        limit: Max results to return

    Returns:
        {
            "enforcement_actions": List[Dict],
            "count": int,
            "source": str
        }
    """
    logger.info(f"Searching FDA enforcement for {company_name}")

    try:
        rate_limit("openfda", min_interval_seconds=0.25)  # 240 req/min = 4 req/sec

        url = "https://api.fda.gov/drug/enforcement.json"
        params = {
            "search": f'openfda.manufacturer_name:"{company_name}"',
            "limit": limit
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        enforcement_actions = []
        for item in results:
            enforcement_actions.append({
                "classification": item.get("classification"),
                "status": item.get("status"),
                "recall_initiation_date": item.get("recall_initiation_date"),
                "product_description": item.get("product_description"),
                "reason_for_recall": item.get("reason_for_recall")
            })

        result = {
            "enforcement_actions": enforcement_actions,
            "count": len(enforcement_actions),
            "source": "openfda_api"
        }

        logger.info(f"Found {len(enforcement_actions)} enforcement actions for {company_name}")
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # No results found
            return {
                "enforcement_actions": [],
                "count": 0,
                "source": "openfda_api"
            }
        else:
            logger.error(f"HTTP error searching FDA enforcement: {e}")
            return {
                "enforcement_actions": [],
                "count": 0,
                "source": "error",
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Error searching FDA enforcement for {company_name}: {e}")
        return {
            "enforcement_actions": [],
            "count": 0,
            "source": "error",
            "error": str(e)
        }


def main():
    """CLI interface for regulatory data fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch FDA regulatory data")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # check_form_483 command
    parser_483 = subparsers.add_parser("check_483", help="Check for Form 483 with OAI")
    parser_483.add_argument("company_name", help="Company name")
    parser_483.add_argument("--lookback-years", type=int, default=3, help="Years to look back")

    # check_ema_approval command
    parser_ema = subparsers.add_parser("check_ema", help="Check EMA approval status")
    parser_ema.add_argument("drug_name", help="Drug name")

    # classify_crl command
    parser_crl = subparsers.add_parser("classify_crl", help="Classify CRL as Class 1 or 2")
    parser_crl.add_argument("ticker", help="Stock ticker")
    parser_crl.add_argument("drug_name", help="Drug name")

    # search_enforcement command
    parser_enforcement = subparsers.add_parser("search_enforcement", help="Search FDA enforcement actions")
    parser_enforcement.add_argument("company_name", help="Company name")
    parser_enforcement.add_argument("--limit", type=int, default=10, help="Max results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "check_483":
        result = check_form_483(args.company_name, args.lookback_years)
        print(json.dumps(result, indent=2))

    elif args.command == "check_ema":
        result = check_ema_approval(args.drug_name)
        print(json.dumps(result, indent=2))

    elif args.command == "classify_crl":
        result = classify_crl(args.ticker, args.drug_name)
        print(json.dumps(result, indent=2))

    elif args.command == "search_enforcement":
        result = search_fda_enforcement(args.company_name, args.limit)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
