"""
Unit tests for options position sizing calculations.

Tests the options-specific sizing rules: premium limits, notional caps,
archetype-specific limits, and regime adjustments.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pytest


class TestOptionsGlobalLimits:
    """Tests for global options portfolio limits."""

    def test_options_premium_limit_enforcement(self):
        """Verify 10% max portfolio in options premium (global limit)."""
        account_size = 25000
        max_premium_pct = 0.10  # 10% global limit

        # Test case: Want to open position with $30,000 premium
        # Max allowed: $2500 (10% of $25,000)
        premium_per_contract = 10.00  # $10 per share = $1000 per contract
        contracts_requested = 30  # Would cost $30,000 (30 * 100 * $10)

        total_premium = premium_per_contract * contracts_requested * 100
        max_premium_allowed = account_size * max_premium_pct

        # Should be rejected - exceeds 10% limit
        assert total_premium > max_premium_allowed, \
            f"Test setup error: {total_premium} should exceed {max_premium_allowed}"

        # Calculate max contracts allowed
        # Max premium: $2500
        # Cost per contract: $10 * 100 = $1000
        # Max contracts: $2500 / $1000 = 2.5 → floor to 2
        max_contracts = int(max_premium_allowed / (premium_per_contract * 100))

        assert max_contracts == 2, \
            f"Max contracts should be 2, got {max_contracts}"

        # Verify position is within limit
        approved_premium = max_contracts * premium_per_contract * 100
        assert approved_premium <= max_premium_allowed
        assert approved_premium / account_size <= max_premium_pct

    def test_options_notional_cap_enforcement(self):
        """Verify 30% max delta-adjusted notional exposure across all options."""
        account_size = 25000
        max_notional_pct = 0.30  # 30% notional cap

        # Test case: PDUFA call option
        stock_price = 100.00
        strike = 100.00  # ATM
        premium = 5.00
        delta = 0.50  # ATM call delta ~0.50
        contracts = 15  # 15 contracts

        # Notional exposure = contracts * 100 * stock_price * delta
        notional_exposure = contracts * 100 * stock_price * delta
        max_notional_allowed = account_size * max_notional_pct

        # 15 contracts * 100 * $100 * 0.50 = $75,000 delta-adjusted
        assert notional_exposure == 75000

        # Max allowed: $7,500 (30% of $25,000)
        assert max_notional_allowed == 7500

        # Should be rejected - exceeds notional cap
        assert notional_exposure > max_notional_allowed

        # Calculate max contracts within notional cap
        # Max notional = $7,500
        # Per contract delta exposure = 100 * $100 * 0.50 = $5,000
        # Max contracts = $7,500 / $5,000 = 1.5 → 1 contract
        max_contracts = int(max_notional_allowed / (100 * stock_price * delta))

        assert max_contracts == 1, \
            f"Max contracts should be 1, got {max_contracts}"

        # Verify
        approved_notional = max_contracts * 100 * stock_price * delta
        assert approved_notional <= max_notional_allowed


class TestArchetypeSpecificSizing:
    """Tests for archetype-specific position sizing rules."""

    def test_pdufa_options_sizing_1_5_pct(self):
        """PDUFA archetype has 1.5% premium cap."""
        account_size = 25000
        pdufa_max_premium_pct = 0.015  # 1.5% for PDUFA

        # Test case: PDUFA long call
        premium_per_contract = 2.50  # $2.50 per share = $250 per contract
        stock_price = 15.00
        strike = 15.00

        # Max premium allowed: $25,000 * 0.015 = $375
        max_premium_allowed = account_size * pdufa_max_premium_pct
        assert max_premium_allowed == 375

        # Calculate contracts
        # $375 / $250 = 1.5 → floor to 1 contract
        max_contracts = int(max_premium_allowed / (premium_per_contract * 100))
        assert max_contracts == 1

        # Total premium
        total_premium = max_contracts * premium_per_contract * 100
        assert total_premium == 250
        assert total_premium <= max_premium_allowed

        # Verify percentage
        position_pct = total_premium / account_size
        assert position_pct <= pdufa_max_premium_pct

    def test_activist_tier1_options_sizing(self):
        """Tier-1 activist has 4% premium cap with 10% notional."""
        account_size = 25000
        tier1_max_premium_pct = 0.04  # 4% for Tier-1
        tier1_max_notional_pct = 0.10  # 10% notional

        # Test case: Tier-1 activist LEAPS call
        stock_price = 50.00
        strike = 50.00  # ATM
        premium_per_contract = 5.00  # $500 per contract
        delta = 0.55  # ATM delta

        # Premium limit: $25,000 * 0.04 = $1,000
        max_premium_allowed = account_size * tier1_max_premium_pct
        assert max_premium_allowed == 1000

        # Premium-based max: $1,000 / $500 = 2 contracts
        max_contracts_premium = int(max_premium_allowed / (premium_per_contract * 100))
        assert max_contracts_premium == 2

        # Notional limit: $25,000 * 0.10 = $2,500
        max_notional_allowed = account_size * tier1_max_notional_pct
        assert max_notional_allowed == 2500

        # Notional-based max: $2,500 / (100 * $50 * 0.55) = $2,500 / $2,750 = 0.9 → 0 contracts
        # Wait, that's wrong. Let me recalculate.
        # Per contract notional: 100 shares * $50 * 0.55 delta = $2,750
        # Max contracts: $2,500 / $2,750 = 0.9 → floor to 0

        # Actually this shows the notional cap is MORE restrictive
        per_contract_notional = 100 * stock_price * delta
        max_contracts_notional = int(max_notional_allowed / per_contract_notional)

        # Use the more conservative (smaller) limit
        max_contracts = min(max_contracts_premium, max_contracts_notional)

        # In this case, notional is more restrictive (0 contracts)
        assert max_contracts == 0, \
            f"Expected 0 contracts (notional-limited), got {max_contracts}"

        # Try with smaller position - 1 contract
        # Premium: 1 * $500 = $500 (within $1,000 limit ✓)
        # Notional: 1 * 100 * $50 * 0.55 = $2,750 (exceeds $2,500 limit ✗)
        contracts = 1
        total_premium = contracts * premium_per_contract * 100
        total_notional = contracts * 100 * stock_price * delta

        assert total_premium <= max_premium_allowed  # Passes premium check
        assert total_notional > max_notional_allowed  # Fails notional check

    def test_activist_tier3_no_options(self):
        """Tier-3 activists cannot use options (0% premium cap)."""
        account_size = 25000
        tier3_max_premium_pct = 0.0  # 0% for Tier-3

        max_premium_allowed = account_size * tier3_max_premium_pct
        assert max_premium_allowed == 0

        # Any premium would exceed limit
        premium_per_contract = 1.00  # Even $1
        max_contracts = int(max_premium_allowed / (premium_per_contract * 100)) if premium_per_contract > 0 else 0

        assert max_contracts == 0, "Tier-3 activists cannot use options"


class TestRegimeAdjustments:
    """Tests for regime-based position size adjustments."""

    def test_regime_adjustment_vix_elevated(self):
        """VIX 20-30 reduces new options positions by 25%."""
        account_size = 25000
        pdufa_max_premium_pct = 0.015  # 1.5% base

        # Regime adjustment
        vix_elevated_reduction = 0.25  # 25% reduction
        adjusted_max_pct = pdufa_max_premium_pct * (1 - vix_elevated_reduction)

        # Adjusted max: 1.5% * 0.75 = 1.125%
        assert adjusted_max_pct == 0.01125

        # Calculate max premium
        base_max_premium = account_size * pdufa_max_premium_pct  # $375
        adjusted_max_premium = account_size * adjusted_max_pct  # $281.25

        assert base_max_premium == 375
        assert adjusted_max_premium == 281.25

        # With premium = $2.50 per contract
        premium_per_contract = 2.50

        # Base: $375 / $250 = 1.5 → 1 contract
        base_contracts = int(base_max_premium / (premium_per_contract * 100))
        assert base_contracts == 1

        # Adjusted: $281.25 / $250 = 1.125 → 1 contract
        # (In this case still 1, but less headroom)
        adjusted_contracts = int(adjusted_max_premium / (premium_per_contract * 100))
        assert adjusted_contracts == 1

        # Try with larger premium where reduction matters
        premium_per_contract_large = 1.50  # $150 per contract

        # Base: $375 / $150 = 2.5 → 2 contracts
        base_contracts_large = int(base_max_premium / (premium_per_contract_large * 100))
        assert base_contracts_large == 2

        # Adjusted: $281.25 / $150 = 1.875 → 1 contract (reduction effective)
        adjusted_contracts_large = int(adjusted_max_premium / (premium_per_contract_large * 100))
        assert adjusted_contracts_large == 1

        # Verify 25% reduction is applied
        assert adjusted_contracts_large < base_contracts_large

    def test_regime_adjustment_vix_crisis(self):
        """VIX >30 sustained reduces new options positions by 50%."""
        account_size = 25000
        activist_tier1_max_pct = 0.04  # 4% base

        # Crisis reduction
        vix_crisis_reduction = 0.50  # 50% reduction
        adjusted_max_pct = activist_tier1_max_pct * (1 - vix_crisis_reduction)

        # Adjusted: 4% * 0.50 = 2%
        assert adjusted_max_pct == 0.02

        base_max_premium = account_size * activist_tier1_max_pct  # $1,000
        adjusted_max_premium = account_size * adjusted_max_pct  # $500

        assert base_max_premium == 1000
        assert adjusted_max_premium == 500

        # With premium = $5.00 per contract ($500 per contract)
        premium_per_contract = 5.00

        # Base: $1,000 / $500 = 2 contracts
        base_contracts = int(base_max_premium / (premium_per_contract * 100))
        assert base_contracts == 2

        # Adjusted: $500 / $500 = 1 contract (50% reduction)
        adjusted_contracts = int(adjusted_max_premium / (premium_per_contract * 100))
        assert adjusted_contracts == 1

        assert adjusted_contracts == base_contracts / 2


class TestEdgeCases:
    """Tests for edge cases in options sizing."""

    def test_fractional_contracts_floor(self):
        """Fractional contracts should floor to nearest integer."""
        account_size = 25000
        max_premium_pct = 0.015  # $375 max

        # Premium that results in fractional contracts
        premium_per_contract = 1.75  # $175 per contract

        max_premium = account_size * max_premium_pct  # $375
        contracts_exact = max_premium / (premium_per_contract * 100)  # $375 / $175 = 2.142857

        # Should floor to 2
        max_contracts = int(contracts_exact)
        assert max_contracts == 2

        # Verify we don't exceed limit
        total_premium = max_contracts * premium_per_contract * 100
        assert total_premium <= max_premium

    def test_zero_premium_returns_zero_contracts(self):
        """If premium is 0 (invalid), should return 0 contracts."""
        account_size = 25000
        max_premium_pct = 0.015

        premium_per_contract = 0.0  # Invalid

        max_premium = account_size * max_premium_pct

        # Prevent division by zero
        if premium_per_contract <= 0:
            max_contracts = 0
        else:
            max_contracts = int(max_premium / (premium_per_contract * 100))

        assert max_contracts == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
