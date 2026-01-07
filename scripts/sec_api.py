"""
SEC API Module

Fetches financial data from SEC EDGAR API for kill screen calculations:
- Beneish M-Score (earnings manipulation detection)
- Altman Z-Score (bankruptcy prediction)

Primary source: SEC XBRL API
Fallback: Manual calculation from 10-Q/10-K filings
"""

import json
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FinancialData:
    """Container for financial metrics needed for kill screens."""
    # Balance Sheet
    total_assets: float
    current_assets: float
    total_liabilities: float
    current_liabilities: float
    retained_earnings: float
    working_capital: float
    ppe: float  # Property, plant, equipment (for M-Score)
    long_term_debt: float

    # Income Statement
    revenue: float
    ebit: float  # Earnings before interest and tax
    net_income: float
    gross_profit: float
    sga_expenses: float  # Selling, general & admin
    depreciation: float
    accounts_receivable: float

    # Cash Flow
    operating_cash_flow: float
    cash_and_equivalents: float

    # Other
    market_cap: float
    shares_outstanding: float

    # Metadata
    filing_date: str
    fiscal_period: str
    source: str = "SEC API"


def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Get CIK (Central Index Key) from ticker symbol.

    Uses SEC company tickers JSON mapping.

    Args:
        ticker: Stock ticker symbol

    Returns:
        CIK string (zero-padded to 10 digits), or None if not found
    """
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "Trading System research@example.com"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        ticker = ticker.upper()

        for entry in data.values():
            if entry.get("ticker") == ticker:
                cik = str(entry["cik_str"]).zfill(10)
                return cik

        return None

    except Exception as e:
        print(f"Error getting CIK for {ticker}: {e}", file=sys.stderr)
        return None


def get_company_facts(cik: str) -> Optional[Dict]:
    """
    Fetch company facts from SEC XBRL API.

    API: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json

    Args:
        cik: Company CIK (10-digit zero-padded)

    Returns:
        Dict with company facts, or None if fetch fails
    """
    try:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        headers = {"User-Agent": "Trading System research@example.com"}

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        print(f"Error fetching company facts for CIK {cik}: {e}", file=sys.stderr)
        return None


def extract_latest_value(facts: Dict, concept: str, taxonomy: str = "us-gaap") -> Optional[float]:
    """
    Extract latest value for a given XBRL concept.

    Args:
        facts: Company facts dict from SEC API
        concept: XBRL concept name (e.g., "Assets", "Liabilities")
        taxonomy: XBRL taxonomy (default: "us-gaap")

    Returns:
        Latest value for the concept, or None if not found
    """
    try:
        if taxonomy not in facts.get("facts", {}):
            return None

        if concept not in facts["facts"][taxonomy]:
            return None

        units = facts["facts"][taxonomy][concept].get("units", {})

        # Try USD first, then shares
        for unit_type in ["USD", "shares", "pure"]:
            if unit_type in units:
                values = units[unit_type]
                # Sort by filing date, get most recent
                sorted_values = sorted(values, key=lambda x: x.get("end", ""), reverse=True)

                for value in sorted_values:
                    if "val" in value:
                        return float(value["val"])

        return None

    except (KeyError, ValueError, TypeError) as e:
        print(f"Error extracting {concept}: {e}", file=sys.stderr)
        return None


def extract_two_periods(facts: Dict, concept: str, taxonomy: str = "us-gaap") -> Tuple[Optional[float], Optional[float]]:
    """
    Extract latest TWO values for a given XBRL concept (for M-Score calculation).

    Args:
        facts: Company facts dict from SEC API
        concept: XBRL concept name
        taxonomy: XBRL taxonomy (default: "us-gaap")

    Returns:
        Tuple of (current_value, previous_value), or (None, None) if not found
    """
    try:
        if taxonomy not in facts.get("facts", {}):
            return (None, None)

        if concept not in facts["facts"][taxonomy]:
            return (None, None)

        units = facts["facts"][taxonomy][concept].get("units", {})

        for unit_type in ["USD", "shares", "pure"]:
            if unit_type in units:
                values = units[unit_type]
                # Sort by end date (most recent first)
                sorted_values = sorted(
                    [v for v in values if "val" in v],
                    key=lambda x: x.get("end", ""),
                    reverse=True
                )

                if len(sorted_values) >= 2:
                    current = float(sorted_values[0]["val"])
                    previous = float(sorted_values[1]["val"])
                    return (current, previous)
                elif len(sorted_values) == 1:
                    return (float(sorted_values[0]["val"]), None)

        return (None, None)

    except (KeyError, ValueError, TypeError) as e:
        print(f"Error extracting two periods for {concept}: {e}", file=sys.stderr)
        return (None, None)


def parse_financials(ticker: str, cik: Optional[str] = None) -> Optional[FinancialData]:
    """
    Parse financial data from SEC API for kill screen calculations.

    Args:
        ticker: Stock ticker symbol
        cik: Optional CIK (will be looked up if not provided)

    Returns:
        FinancialData object, or None if fetch/parse fails
    """
    if not cik:
        cik = get_cik_from_ticker(ticker)
        if not cik:
            print(f"Could not find CIK for {ticker}", file=sys.stderr)
            return None

    facts = get_company_facts(cik)
    if not facts:
        return None

    # Extract key metrics
    try:
        # Basic balance sheet
        total_assets = extract_latest_value(facts, "Assets") or 0
        current_assets = extract_latest_value(facts, "AssetsCurrent") or 0
        current_liabilities = extract_latest_value(facts, "LiabilitiesCurrent") or 0

        # Try multiple XBRL tags for revenue (companies use different ones)
        revenue = (extract_latest_value(facts, "Revenues") or
                  extract_latest_value(facts, "RevenueFromContractWithCustomerExcludingAssessedTax") or
                  extract_latest_value(facts, "SalesRevenueNet") or 0)

        # Gross profit (Revenue - COGS)
        gross_profit = extract_latest_value(facts, "GrossProfit") or 0

        return FinancialData(
            total_assets=total_assets,
            current_assets=current_assets,
            total_liabilities=extract_latest_value(facts, "Liabilities") or 0,
            current_liabilities=current_liabilities,
            retained_earnings=extract_latest_value(facts, "RetainedEarningsAccumulatedDeficit") or 0,
            working_capital=current_assets - current_liabilities,
            ppe=extract_latest_value(facts, "PropertyPlantAndEquipmentNet") or 0,
            long_term_debt=extract_latest_value(facts, "LongTermDebt") or 0,
            revenue=revenue,
            ebit=extract_latest_value(facts, "OperatingIncomeLoss") or 0,
            net_income=extract_latest_value(facts, "NetIncomeLoss") or 0,
            gross_profit=gross_profit,
            sga_expenses=extract_latest_value(facts, "SellingGeneralAndAdministrativeExpense") or 0,
            depreciation=extract_latest_value(facts, "DepreciationDepletionAndAmortization") or 0,
            accounts_receivable=extract_latest_value(facts, "AccountsReceivableNetCurrent") or 0,
            operating_cash_flow=extract_latest_value(facts, "NetCashProvidedByUsedInOperatingActivities") or 0,
            cash_and_equivalents=extract_latest_value(facts, "CashAndCashEquivalentsAtCarryingValue") or 0,
            market_cap=0,  # Will be calculated separately from price data
            shares_outstanding=extract_latest_value(facts, "CommonStockSharesOutstanding") or 0,
            filing_date=datetime.now().isoformat(),
            fiscal_period="Latest available",
            source="SEC XBRL API"
        )

    except Exception as e:
        print(f"Error parsing financials for {ticker}: {e}", file=sys.stderr)
        return None


def fetch_two_periods(ticker: str, cik: Optional[str] = None) -> Tuple[Optional[FinancialData], Optional[FinancialData]]:
    """
    Fetch current AND previous period financials for M-Score calculation.

    Returns:
        Tuple of (current_period, previous_period)
    """
    if not cik:
        cik = get_cik_from_ticker(ticker)
        if not cik:
            return (None, None)

    facts = get_company_facts(cik)
    if not facts:
        return (None, None)

    try:
        # Extract TWO periods for each metric
        ar_curr, ar_prev = extract_two_periods(facts, "AccountsReceivableNetCurrent")
        rev_curr, rev_prev = extract_two_periods(facts, "Revenues")
        if not rev_curr:
            rev_curr, rev_prev = extract_two_periods(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")

        ta_curr, ta_prev = extract_two_periods(facts, "Assets")
        ca_curr, ca_prev = extract_two_periods(facts, "AssetsCurrent")
        cl_curr, cl_prev = extract_two_periods(facts, "LiabilitiesCurrent")
        ppe_curr, ppe_prev = extract_two_periods(facts, "PropertyPlantAndEquipmentNet")
        gp_curr, gp_prev = extract_two_periods(facts, "GrossProfit")
        sga_curr, sga_prev = extract_two_periods(facts, "SellingGeneralAndAdministrativeExpense")
        dep_curr, dep_prev = extract_two_periods(facts, "DepreciationDepletionAndAmortization")
        ltd_curr, ltd_prev = extract_two_periods(facts, "LongTermDebt")
        cash_curr, cash_prev = extract_two_periods(facts, "CashAndCashEquivalentsAtCarryingValue")

        # Build current period
        current = FinancialData(
            total_assets=ta_curr or 0,
            current_assets=ca_curr or 0,
            total_liabilities=extract_latest_value(facts, "Liabilities") or 0,
            current_liabilities=cl_curr or 0,
            retained_earnings=extract_latest_value(facts, "RetainedEarningsAccumulatedDeficit") or 0,
            working_capital=(ca_curr or 0) - (cl_curr or 0),
            ppe=ppe_curr or 0,
            long_term_debt=ltd_curr or 0,
            revenue=rev_curr or 0,
            ebit=extract_latest_value(facts, "OperatingIncomeLoss") or 0,
            net_income=extract_latest_value(facts, "NetIncomeLoss") or 0,
            gross_profit=gp_curr or 0,
            sga_expenses=sga_curr or 0,
            depreciation=dep_curr or 0,
            accounts_receivable=ar_curr or 0,
            operating_cash_flow=extract_latest_value(facts, "NetCashProvidedByUsedInOperatingActivities") or 0,
            cash_and_equivalents=cash_curr or 0,
            market_cap=0,
            shares_outstanding=extract_latest_value(facts, "CommonStockSharesOutstanding") or 0,
            filing_date=datetime.now().isoformat(),
            fiscal_period="Current",
            source="SEC XBRL API"
        )

        # Build previous period (if available)
        if ta_prev and rev_prev:
            previous = FinancialData(
                total_assets=ta_prev,
                current_assets=ca_prev or 0,
                total_liabilities=0,  # Not needed for M-Score ratios
                current_liabilities=cl_prev or 0,
                retained_earnings=0,
                working_capital=(ca_prev or 0) - (cl_prev or 0),
                ppe=ppe_prev or 0,
                long_term_debt=ltd_prev or 0,
                revenue=rev_prev,
                ebit=0,
                net_income=0,
                gross_profit=gp_prev or 0,
                sga_expenses=sga_prev or 0,
                depreciation=dep_prev or 0,
                accounts_receivable=ar_prev or 0,
                operating_cash_flow=0,
                cash_and_equivalents=cash_prev or 0,
                market_cap=0,
                shares_outstanding=0,
                filing_date="",
                fiscal_period="Previous",
                source="SEC XBRL API"
            )
            return (current, previous)
        else:
            return (current, None)

    except Exception as e:
        print(f"Error fetching two periods for {ticker}: {e}", file=sys.stderr)
        return (None, None)


def calculate_m_score(current: FinancialData, previous: Optional[FinancialData] = None) -> Optional[float]:
    """
    Calculate Beneish M-Score for earnings manipulation detection.

    M-Score > -1.78 suggests possible manipulation (FAIL kill screen).

    Formula (8 variables):
    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

    Args:
        current: Current period financial data
        previous: Previous period financial data (required for M-Score)

    Returns:
        M-Score value, or None if calculation fails
    """
    if not previous:
        print("M-Score requires previous period data - not available", file=sys.stderr)
        return None

    try:
        # Helper function to avoid division by zero
        def safe_ratio(numerator, denominator, default=1.0):
            if denominator == 0 or denominator is None:
                return default
            return numerator / denominator

        # 1. DSRI (Days Sales in Receivables Index)
        # DSRI = (AR_t / Rev_t) / (AR_t-1 / Rev_t-1)
        dsri_current = safe_ratio(current.accounts_receivable, current.revenue)
        dsri_previous = safe_ratio(previous.accounts_receivable, previous.revenue)
        dsri = safe_ratio(dsri_current, dsri_previous)

        # 2. GMI (Gross Margin Index) - INVERSE ratio
        # GMI = (GP_t-1 / Rev_t-1) / (GP_t / Rev_t)
        gm_current = safe_ratio(current.gross_profit, current.revenue)
        gm_previous = safe_ratio(previous.gross_profit, previous.revenue)
        gmi = safe_ratio(gm_previous, gm_current)

        # 3. AQI (Asset Quality Index)
        # AQI = (1 - (CA_t + PPE_t)/TA_t) / (1 - (CA_t-1 + PPE_t-1)/TA_t-1)
        aqi_current = 1 - safe_ratio(current.current_assets + current.ppe, current.total_assets, default=0)
        aqi_previous = 1 - safe_ratio(previous.current_assets + previous.ppe, previous.total_assets, default=0)
        aqi = safe_ratio(aqi_current, aqi_previous)

        # 4. SGI (Sales Growth Index)
        # SGI = Rev_t / Rev_t-1
        sgi = safe_ratio(current.revenue, previous.revenue)

        # 5. DEPI (Depreciation Index)
        # DEPI = (Dep_t-1 / (PPE_t-1 + Dep_t-1)) / (Dep_t / (PPE_t + Dep_t))
        depi_current = safe_ratio(current.depreciation, current.ppe + current.depreciation, default=0)
        depi_previous = safe_ratio(previous.depreciation, previous.ppe + previous.depreciation, default=0)
        depi = safe_ratio(depi_previous, depi_current)

        # 6. SGAI (SG&A Index)
        # SGAI = (SGA_t / Rev_t) / (SGA_t-1 / Rev_t-1)
        sgai_current = safe_ratio(current.sga_expenses, current.revenue)
        sgai_previous = safe_ratio(previous.sga_expenses, previous.revenue)
        sgai = safe_ratio(sgai_current, sgai_previous)

        # 7. LVGI (Leverage Index)
        # LVGI = ((LTD_t + CL_t) / TA_t) / ((LTD_t-1 + CL_t-1) / TA_t-1)
        lvgi_current = safe_ratio(current.long_term_debt + current.current_liabilities, current.total_assets)
        lvgi_previous = safe_ratio(previous.long_term_debt + previous.current_liabilities, previous.total_assets)
        lvgi = safe_ratio(lvgi_current, lvgi_previous)

        # 8. TATA (Total Accruals to Total Assets)
        # TATA = (ΔWC - ΔCash - Dep_t) / TA_t
        delta_wc = current.working_capital - previous.working_capital
        delta_cash = current.cash_and_equivalents - previous.cash_and_equivalents
        tata = safe_ratio(delta_wc - delta_cash - current.depreciation, current.total_assets, default=0)

        # Calculate M-Score
        m_score = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )

        return m_score

    except Exception as e:
        print(f"M-Score calculation error: {e}", file=sys.stderr)
        return None


def calculate_z_score(financials: FinancialData, industry: str = "general") -> Optional[float]:
    """
    Calculate Altman Z-Score for bankruptcy prediction.

    Z-Score Formula (manufacturing companies):
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Where:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Revenue / Total Assets

    Z-Score thresholds (industry-adjusted):
    - General: 1.81
    - Biotech/Pharma: 1.5
    - Software/SaaS: 2.0
    - Utilities: 2.5

    Args:
        financials: Financial data
        industry: Industry for threshold adjustment

    Returns:
        Z-Score value, or None if calculation fails
    """
    try:
        if financials.total_assets == 0:
            return None

        # Calculate components
        x1 = financials.working_capital / financials.total_assets
        x2 = financials.retained_earnings / financials.total_assets
        x3 = financials.ebit / financials.total_assets

        # X4 requires market cap (from price data)
        if financials.market_cap > 0 and financials.total_liabilities > 0:
            x4 = financials.market_cap / financials.total_liabilities
        else:
            x4 = 0  # Missing market cap data

        x5 = financials.revenue / financials.total_assets if financials.revenue > 0 else 0

        # Calculate Z-Score
        z_score = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (1.0 * x5)

        return z_score

    except (ZeroDivisionError, TypeError) as e:
        print(f"Z-Score calculation error: {e}", file=sys.stderr)
        return None


def get_latest_filing_date(cik: str) -> Optional[str]:
    """
    Get the date of the most recent SEC filing.

    Used for cache invalidation logic.

    Args:
        cik: Company CIK

    Returns:
        ISO date string of latest filing, or None
    """
    try:
        facts = get_company_facts(cik)
        if not facts:
            return None

        # Extract filing dates from any concept's values
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        latest_date = None

        for concept_data in us_gaap.values():
            units = concept_data.get("units", {})
            for unit_values in units.values():
                for value in unit_values:
                    filed = value.get("filed")
                    if filed and (not latest_date or filed > latest_date):
                        latest_date = filed

        return latest_date

    except Exception as e:
        print(f"Error getting latest filing date: {e}", file=sys.stderr)
        return None


def main():
    """CLI interface for testing SEC API."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch SEC financial data and calculate kill screens")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--cik", help="Optional CIK (will be looked up if not provided)")
    parser.add_argument("--m-score", action="store_true", help="Calculate M-Score")
    parser.add_argument("--z-score", action="store_true", help="Calculate Z-Score")
    parser.add_argument("--industry", default="general", help="Industry for Z-Score adjustment")

    args = parser.parse_args()

    financials = parse_financials(args.ticker, args.cik)

    if not financials:
        print(f"ERROR: Could not fetch financials for {args.ticker}", file=sys.stderr)
        sys.exit(1)

    output = {
        "ticker": args.ticker.upper(),
        "financials": {
            "total_assets": financials.total_assets,
            "current_assets": financials.current_assets,
            "total_liabilities": financials.total_liabilities,
            "current_liabilities": financials.current_liabilities,
            "working_capital": financials.working_capital,
            "revenue": financials.revenue,
            "ebit": financials.ebit,
            "net_income": financials.net_income,
            "filing_date": financials.filing_date,
            "source": financials.source
        }
    }

    if args.m_score:
        m_score = calculate_m_score(financials)
        output["m_score"] = m_score
        output["m_score_threshold"] = -1.78
        output["m_score_pass"] = m_score is not None and m_score <= -1.78

    if args.z_score:
        z_score = calculate_z_score(financials, args.industry)
        output["z_score"] = z_score

        # Industry-adjusted threshold
        thresholds = {
            "biotech": 1.5,
            "pharma": 1.5,
            "software": 2.0,
            "saas": 2.0,
            "utilities": 2.5,
            "general": 1.81
        }
        threshold = thresholds.get(args.industry.lower(), 1.81)

        output["z_score_threshold"] = threshold
        output["z_score_pass"] = z_score is not None and z_score >= threshold

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
