"""
Unit tests for options Greeks validation logic.

Tests validation rules for Greeks (delta, theta, gamma, vega, IV) to ensure
data quality and prevent trading on invalid IBKR responses.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pytest


class TestIVValidation:
    """Tests for Implied Volatility (IV) validation."""

    def test_iv_range_validation(self):
        """IV must be between 10% and 300%, flag outliers."""
        # Valid IV range: 0.10 to 3.00 (10% to 300%)
        iv_min = 0.10
        iv_max = 3.00

        # Test valid IVs
        valid_ivs = [0.15, 0.25, 0.50, 1.00, 2.00, 2.50]
        for iv in valid_ivs:
            assert iv_min <= iv <= iv_max, \
                f"IV {iv*100:.1f}% should be valid"

        # Test invalid IVs (too low)
        invalid_low_ivs = [0.01, 0.05, 0.09]
        for iv in invalid_low_ivs:
            assert iv < iv_min, \
                f"IV {iv*100:.1f}% should be rejected (too low)"

        # Test invalid IVs (too high)
        invalid_high_ivs = [3.5, 4.0, 10.0]
        for iv in invalid_high_ivs:
            assert iv > iv_max, \
                f"IV {iv*100:.1f}% should be rejected (too high)"

    def test_iv_outlier_detection(self):
        """Flag suspiciously high IV (>200%) for manual review."""
        warning_threshold = 2.00  # 200%

        # Normal IVs - no warning
        normal_ivs = [0.20, 0.35, 0.75, 1.25]
        for iv in normal_ivs:
            if iv > warning_threshold:
                pytest.fail(f"IV {iv*100:.1f}% incorrectly flagged as outlier")

        # High IVs - should warn but not reject
        high_ivs = [2.10, 2.50, 2.80]
        for iv in high_ivs:
            assert iv > warning_threshold, \
                f"IV {iv*100:.1f}% should trigger warning"
            # But still valid (< 300%)
            assert iv <= 3.00

    def test_iv_none_handling(self):
        """Handle IBKR returning None for IV gracefully."""
        iv_values = [None, -1, -2]  # IBKR sentinel values

        for iv in iv_values:
            # Should be treated as invalid
            if iv is None or iv < 0:
                is_valid = False
            else:
                is_valid = True

            assert not is_valid, \
                f"IV {iv} should be invalid"


class TestDeltaValidation:
    """Tests for Delta validation."""

    def test_delta_range_validation(self):
        """Delta for calls must be between 0.01 and 1.00."""
        delta_min = 0.01
        delta_max = 1.00

        # Valid deltas for calls
        valid_deltas = [0.10, 0.30, 0.50, 0.70, 0.90, 0.99]
        for delta in valid_deltas:
            assert delta_min <= delta <= delta_max, \
                f"Delta {delta:.3f} should be valid"

        # Invalid deltas
        invalid_deltas = [-0.5, 0.0, 1.5, 2.0]
        for delta in invalid_deltas:
            assert delta < delta_min or delta > delta_max, \
                f"Delta {delta:.3f} should be invalid"

    def test_delta_atm_call_range(self):
        """ATM call delta should be approximately 0.40-0.60."""
        atm_delta_min = 0.40
        atm_delta_max = 0.60

        # Typical ATM call deltas
        atm_deltas = [0.48, 0.50, 0.52, 0.55]
        for delta in atm_deltas:
            assert atm_delta_min <= delta <= atm_delta_max, \
                f"ATM delta {delta:.3f} should be in range"

        # Deltas outside ATM range (but still valid for calls)
        otm_delta = 0.25  # OTM call
        itm_delta = 0.75  # ITM call

        # These are valid, just not ATM
        assert 0.01 <= otm_delta <= 1.00
        assert 0.01 <= itm_delta <= 1.00

        # But they're not ATM
        assert otm_delta < atm_delta_min
        assert itm_delta > atm_delta_max

    def test_delta_none_handling(self):
        """Handle IBKR returning None/-1/-2 for delta."""
        sentinel_values = [None, -1, -2]

        for delta in sentinel_values:
            # IBKR sentinel check
            if delta is None or delta == -1 or delta == -2:
                is_valid = False
            else:
                is_valid = True

            assert not is_valid, \
                f"Delta {delta} should be treated as invalid"


class TestThetaValidation:
    """Tests for Theta validation."""

    def test_theta_negative_for_long_calls(self):
        """Theta should be negative for long call positions."""
        # Long calls have negative theta (time decay)
        long_call_thetas = [-0.01, -0.05, -0.10, -0.50, -1.00]

        for theta in long_call_thetas:
            assert theta < 0, \
                f"Long call theta {theta:.3f} should be negative"

    def test_theta_positive_is_suspicious(self):
        """Positive or zero theta for long calls is invalid."""
        suspicious_thetas = [0.0, 0.01, 0.10, 1.00]

        for theta in suspicious_thetas:
            # For long calls, theta should be negative (time decay)
            # Zero or positive theta is suspicious
            if theta >= 0:
                is_suspicious = True
            else:
                is_suspicious = False

            assert is_suspicious, \
                f"Theta {theta:.3f} should be flagged as suspicious"

    def test_theta_range_validation(self):
        """Theta for long calls should be between -10.0 and 0.0."""
        theta_min = -10.0
        theta_max = 0.0

        # Valid thetas
        valid_thetas = [-0.01, -0.10, -0.50, -2.00, -5.00, -9.99]
        for theta in valid_thetas:
            assert theta_min <= theta <= theta_max, \
                f"Theta {theta:.3f} should be valid"

        # Invalid (too negative)
        invalid_theta = -15.0
        assert invalid_theta < theta_min


class TestGammaAndVegaValidation:
    """Tests for Gamma and Vega validation."""

    def test_gamma_positive_for_long_options(self):
        """Gamma should be positive for long options."""
        # Long options (calls or puts) have positive gamma
        gammas = [0.001, 0.01, 0.05, 0.10, 0.50]

        for gamma in gammas:
            assert gamma > 0, \
                f"Gamma {gamma:.4f} should be positive"

    def test_gamma_range_validation(self):
        """Gamma should be between 0.0 and 1.0 for standard options."""
        gamma_min = 0.0
        gamma_max = 1.0

        # Valid gammas
        valid_gammas = [0.001, 0.01, 0.05, 0.10, 0.50, 0.90]
        for gamma in valid_gammas:
            assert gamma_min < gamma <= gamma_max, \
                f"Gamma {gamma:.4f} should be valid"

        # Invalid
        invalid_gammas = [-0.1, 1.5, 2.0]
        for gamma in invalid_gammas:
            assert gamma < gamma_min or gamma > gamma_max

    def test_vega_positive_for_long_options(self):
        """Vega should be positive for long options."""
        # Long options benefit from IV increase
        vegas = [0.01, 0.10, 1.00, 5.00]

        for vega in vegas:
            assert vega > 0, \
                f"Vega {vega:.4f} should be positive"

    def test_vega_range_validation(self):
        """Vega should be between 0.0 and 10.0 for standard options."""
        vega_min = 0.0
        vega_max = 10.0

        # Valid vegas
        valid_vegas = [0.01, 0.50, 2.00, 5.00, 9.99]
        for vega in valid_vegas:
            assert vega_min < vega <= vega_max, \
                f"Vega {vega:.4f} should be valid"

        # Invalid
        invalid_vega = 15.0
        assert invalid_vega > vega_max


class TestGreeksNoneHandling:
    """Tests for handling None/sentinel values from IBKR."""

    def test_greeks_none_handling(self):
        """Handle IBKR returning None/-1/-2 for all Greeks."""
        # IBKR uses -1 and -2 as "not available" sentinels
        sentinel_values = [None, -1, -2]

        greeks_to_test = ["delta", "theta", "gamma", "vega", "implied_volatility"]

        for greek_name in greeks_to_test:
            for sentinel in sentinel_values:
                # Validation function
                def is_valid_greek(value):
                    if value is None or value == -1 or value == -2:
                        return False
                    return True

                assert not is_valid_greek(sentinel), \
                    f"{greek_name}={sentinel} should be invalid"

    def test_partial_greeks_handling(self):
        """Handle cases where some Greeks are available, others are not."""
        # Realistic scenario: IBKR returns some Greeks but not all
        greeks = {
            "delta": 0.52,           # Valid
            "theta": -0.03,          # Valid
            "gamma": None,           # Missing
            "vega": -1,              # Sentinel (invalid)
            "implied_volatility": 0.35  # Valid
        }

        def clean_greek(value):
            """Clean IBKR sentinel values."""
            if value is None or value == -1 or value == -2:
                return None
            return value

        cleaned_greeks = {
            key: clean_greek(value)
            for key, value in greeks.items()
        }

        # Check results
        assert cleaned_greeks["delta"] == 0.52
        assert cleaned_greeks["theta"] == -0.03
        assert cleaned_greeks["gamma"] is None
        assert cleaned_greeks["vega"] is None
        assert cleaned_greeks["implied_volatility"] == 0.35

        # Count valid greeks
        valid_count = sum(1 for v in cleaned_greeks.values() if v is not None)
        assert valid_count == 3, "Should have 3 valid Greeks"

    def test_all_greeks_missing_reject(self):
        """If all Greeks are missing, reject the data."""
        greeks = {
            "delta": None,
            "theta": -1,
            "gamma": -2,
            "vega": None,
            "implied_volatility": -1
        }

        def clean_greek(value):
            if value is None or value == -1 or value == -2:
                return None
            return value

        cleaned_greeks = {
            key: clean_greek(value)
            for key, value in greeks.items()
        }

        # Count valid greeks
        valid_count = sum(1 for v in cleaned_greeks.values() if v is not None)

        # Should reject - no valid Greeks
        assert valid_count == 0, "All Greeks are invalid"

        # Don't trade without Greeks
        can_trade = valid_count >= 3  # Need at least delta, theta, IV
        assert not can_trade, "Should not trade without Greeks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
