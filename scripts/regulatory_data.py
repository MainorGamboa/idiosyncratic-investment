"""
Regulatory Data Fetcher

Fetches FDA regulatory data for PDUFA archetype analysis using the openFDA API.

Working Functions:
- search_fda_enforcement() - Search FDA drug enforcement reports (recalls, warnings)

Manual Lookups Required (not automatable via API):
- Form 483 with OAI status: Visit FDA FOIA Reading Room
- EMA approval status: Visit EMA medicines database
- CRL classification: Request via FDA FOIA or check company 8-K filings

Data Sources:
- openFDA API (free, public, no auth required)

Usage:
    from regulatory_data import search_fda_enforcement

    # Search FDA enforcement actions
    result = search_fda_enforcement("Pfizer")
"""

import requests
import json
import time
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
LAST_REQUEST_TIME = {}


def rate_limit(api_name: str, min_interval_seconds: float = 0.25):
    """Rate limiter for API calls (respects 240 req/min for openFDA)"""
    global LAST_REQUEST_TIME

    if api_name in LAST_REQUEST_TIME:
        elapsed = time.time() - LAST_REQUEST_TIME[api_name]
        if elapsed < min_interval_seconds:
            time.sleep(min_interval_seconds - elapsed)

    LAST_REQUEST_TIME[api_name] = time.time()


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


# Manual lookup instructions for agent reference
MANUAL_LOOKUP_INSTRUCTIONS = {
    "form_483": {
        "description": "FDA Form 483 with OAI (Official Action Indicated) status",
        "url": "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/fda-warning-letters",
        "instructions": "Search for company name in FDA FOIA Reading Room"
    },
    "ema_approval": {
        "description": "EMA (European Medicines Agency) approval status",
        "url": "https://www.ema.europa.eu/en/medicines",
        "instructions": "Search EMA medicines database for drug name"
    },
    "crl_classification": {
        "description": "CRL (Complete Response Letter) classification",
        "instructions": [
            "Class 1 (manufacturing/labeling issues) = 2 month timeline",
            "Class 2 (efficacy/safety issues) = 6 month timeline",
            "Request CRL letter via FDA FOIA or check company 8-K filings"
        ]
    }
}


def main():
    """CLI interface for regulatory data fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch FDA regulatory data")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # search_enforcement command
    parser_enforcement = subparsers.add_parser("search_enforcement", help="Search FDA enforcement actions")
    parser_enforcement.add_argument("company_name", help="Company name")
    parser_enforcement.add_argument("--limit", type=int, default=10, help="Max results")

    # manual_lookups command (reference only)
    subparsers.add_parser("manual_lookups", help="Show manual lookup instructions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "search_enforcement":
        result = search_fda_enforcement(args.company_name, args.limit)
        print(json.dumps(result, indent=2))

    elif args.command == "manual_lookups":
        print(json.dumps(MANUAL_LOOKUP_INSTRUCTIONS, indent=2))


if __name__ == "__main__":
    main()
