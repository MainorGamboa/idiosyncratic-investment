"""
Unit tests for position sizing calculations.

Tests the Kellner Rule (max 2% portfolio loss) and archetype position caps.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pytest
from order_manager import calculate_position_size


class TestKellnerRule:
    """Tests for Kellner Rule: max 2% portfolio loss per trade."""

    def test_basic_position_sizing(self):
        """Test basic Kellner calculation."""
        account_size = 25000
        max_loss_pct = 0.02  # 2%
        entry_price = 125.50
        stop_price = 95.00
        archetype_max_pct = 0.10  # 10% position cap

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, archetype_max_pct
        )

        # Max loss should be $500 (2% of $25,000)
        risk_per_share = entry_price - stop_price  # $30.50
        max_loss = risk_per_share * shares

        assert max_loss <= account_size * max_loss_pct, \
            f"Max loss ${max_loss} exceeds Kellner limit ${account_size * max_loss_pct}"

    def test_kellner_rule_enforcement(self):
        """Test that Kellner rule is strictly enforced."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 100.00
        stop_price = 80.00  # $20 risk per share
        archetype_max_pct = 1.0  # No archetype limit

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, archetype_max_pct
        )

        # Max loss = $500, risk per share = $20
        # Expected shares = $500 / $20 = 25
        assert shares == 25

        # Verify max loss
        max_loss = (entry_price - stop_price) * shares
        assert max_loss == 500

    def test_tight_stop_increases_position_size(self):
        """Tighter stops allow larger positions (within Kellner limit)."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 50.00
        archetype_max_pct = 1.0

        # Tight stop
        stop_price_tight = 48.00  # $2 risk
        shares_tight = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price_tight, archetype_max_pct
        )

        # Wide stop
        stop_price_wide = 40.00  # $10 risk
        shares_wide = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price_wide, archetype_max_pct
        )

        assert shares_tight > shares_wide, \
            "Tighter stop should allow more shares"


class TestArchetypePositionCaps:
    """Tests for archetype-specific position size limits."""

    def test_pdufa_position_cap(self):
        """PDUFA archetype has 1.5% position cap."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 10.00
        stop_price = 5.00
        pdufa_max_pct = 0.015  # 1.5%

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, pdufa_max_pct
        )

        # Position value must not exceed 1.5% of account
        position_value = shares * entry_price
        max_position_value = account_size * pdufa_max_pct

        assert position_value <= max_position_value, \
            f"Position ${position_value} exceeds PDUFA cap ${max_position_value}"

    def test_merger_arb_position_cap(self):
        """Merger arb has 3% position cap."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 100.00
        stop_price = 90.00
        merger_max_pct = 0.03  # 3%

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, merger_max_pct
        )

        position_value = shares * entry_price
        max_position_value = account_size * merger_max_pct

        assert position_value <= max_position_value

    def test_activist_position_cap(self):
        """Activist has 6% position cap."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 50.00
        stop_price = 40.00
        activist_max_pct = 0.06  # 6%

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, activist_max_pct
        )

        position_value = shares * entry_price
        max_position_value = account_size * activist_max_pct

        assert position_value <= max_position_value


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_risk_returns_zero_shares(self):
        """If stop price == entry price, position size should be 0."""
        shares = calculate_position_size(
            account_size=25000,
            max_loss_pct=0.02,
            entry_price=100.00,
            stop_price=100.00,  # No risk!
            archetype_max_pct=0.10
        )

        assert shares == 0, "Zero risk should result in zero shares"

    def test_negative_risk_returns_zero_shares(self):
        """If stop price > entry price, should return 0."""
        shares = calculate_position_size(
            account_size=25000,
            max_loss_pct=0.02,
            entry_price=100.00,
            stop_price=110.00,  # Stop above entry!
            archetype_max_pct=0.10
        )

        assert shares == 0


    def test_penny_stock_with_tight_cap(self):
        """Test with low-priced stock and tight archetype cap."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 2.00  # Penny stock
        stop_price = 1.50
        pdufa_max_pct = 0.015  # 1.5% cap = $375 max position

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, pdufa_max_pct
        )

        # Archetype cap: $375 / $2 = 187 shares
        # Kellner: $500 / $0.50 = 1000 shares
        # Should use archetype cap (more conservative)
        assert shares <= 187


class TestConservativePositioning:
    """Tests that position sizing uses most conservative constraint."""

    def test_kellner_more_conservative(self):
        """When Kellner is more restrictive, use Kellner."""
        account_size = 25000
        max_loss_pct = 0.02  # $500 max loss
        entry_price = 100.00
        stop_price = 50.00  # $50 risk per share
        archetype_max_pct = 0.50  # 50% position cap (very high)

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, archetype_max_pct
        )

        # Kellner: $500 / $50 = 10 shares
        # Archetype: $12,500 / $100 = 125 shares
        # Should use Kellner (10 shares)
        assert shares == 10

    def test_archetype_more_conservative(self):
        """When archetype cap is more restrictive, use archetype."""
        account_size = 25000
        max_loss_pct = 0.02
        entry_price = 10.00
        stop_price = 9.00  # $1 risk per share
        pdufa_max_pct = 0.015  # 1.5% = $375 max

        shares = calculate_position_size(
            account_size, max_loss_pct, entry_price, stop_price, pdufa_max_pct
        )

        # Kellner: $500 / $1 = 500 shares
        # Archetype: $375 / $10 = 37 shares
        # Should use archetype (37 shares)
        assert shares == 37


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
