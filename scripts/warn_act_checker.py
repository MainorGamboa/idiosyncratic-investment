"""
WARN Act Filing Analyzer

Utility functions for analyzing WARN (Worker Adjustment and Retraining Notification)
Act filing text.

Working Functions:
- analyze_warn_language() - Analyze WARN filing text for contract loss indicators

Manual Lookups Required:
- WARN filing search: Agent performs web search across state databases
- No standardized API exists for WARN filings (50 different state websites)

WARN Act Context:
- Requires employers with 100+ employees to provide 60-day notice of plant closings
- "Loss of contract" language = exit signal for Activist archetype
- WARN filing at SpinCo = reduce Spin-off position size 50%

Usage:
    from warn_act_checker import analyze_warn_language

    # Analyze WARN filing text
    result = analyze_warn_language("Closure due to loss of major contract with customer")
"""

import json
import re
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_warn_language(warn_text: str) -> Dict:
    """
    Analyze WARN filing text for "loss of contract" or similar language.

    Keywords indicating contract loss (triggers exit for Activist archetype):
    - "loss of contract"
    - "contract termination"
    - "customer loss"
    - "loss of business"
    - "contract not renewed"
    - "lost contract"
    - "contract canceled"
    - "contract cancellation"

    Args:
        warn_text: Text of WARN filing (reason for layoff)

    Returns:
        {
            "loss_of_contract": bool,
            "keywords_found": List[str],
            "rationale": str
        }
    """
    logger.info("Analyzing WARN filing language")

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


# Manual lookup instructions for agent reference
MANUAL_LOOKUP_INSTRUCTIONS = {
    "warn_filing_search": {
        "description": "Search for WARN Act filings for a company",
        "instructions": "Search '[company name] WARN Act notice' in Google or check state databases",
        "databases": {
            "california": "https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN",
            "new_york": "https://dol.ny.gov/warn-notices",
            "texas": "https://www.twc.texas.gov/businesses/worker-adjustment-retraining-notification-warn-notices",
            "new_jersey": "https://www.nj.gov/labor/employer-services/warn/",
            "all_states": "https://www.dol.gov/agencies/eta/layoffs/warn"
        }
    },
    "activist_exit_trigger": {
        "description": "WARN filing with 'loss of contract' = EXIT for Activist archetype",
        "steps": [
            "1. Search for WARN filings for the company",
            "2. If found, use analyze_warn_language() to check for contract loss",
            "3. If loss_of_contract=True, trigger EXIT signal"
        ]
    },
    "spinoff_sizing": {
        "description": "WARN filing at SpinCo = reduce position 50%",
        "steps": [
            "1. Search for WARN filings for SpinCo (not parent)",
            "2. If any WARN filing found at SpinCo, reduce position size by 50%"
        ]
    }
}


def main():
    """CLI interface for WARN Act analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze WARN Act filing text")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # analyze_language command
    parser_language = subparsers.add_parser("analyze_language", help="Analyze WARN filing text")
    parser_language.add_argument("warn_text", help="WARN filing text to analyze")

    # manual_lookups command
    subparsers.add_parser("manual_lookups", help="Show manual lookup instructions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "analyze_language":
        result = analyze_warn_language(args.warn_text)
        print(json.dumps(result, indent=2))

    elif args.command == "manual_lookups":
        print(json.dumps(MANUAL_LOOKUP_INSTRUCTIONS, indent=2))


if __name__ == "__main__":
    main()
