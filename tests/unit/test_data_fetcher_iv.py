"""
Unit tests for ATM IV fetching and validation.
"""

import sys
from pathlib import Path
from unittest.mock import patch
import subprocess

# Add scripts and fixtures directories to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))

import data_fetcher
import options_utils
from ibkr_fixtures import mock_subprocess_run_success


class TestATMStrikeSelection:
    """Tests for ATM strike rounding logic."""

    def test_atm_strike_low_price_stock(self):
        increment = options_utils.determine_strike_increment(47.0)
        strike = options_utils.round_to_increment(47.0, increment)
        assert increment == 2.5
        assert strike == 47.5

    def test_atm_strike_mid_price_stock(self):
        increment = options_utils.determine_strike_increment(120.0)
        strike = options_utils.round_to_increment(120.0, increment)
        assert increment == 5.0
        assert strike == 120.0

    def test_atm_strike_high_price_stock(self):
        increment = options_utils.determine_strike_increment(275.0)
        strike = options_utils.round_to_increment(275.0, increment)
        assert increment == 10.0
        assert strike == 280.0


class TestIBKRIVFetch:
    """Tests for IBKR IV fetch handling."""

    def test_ibkr_iv_success_atm(self):
        with patch("data_fetcher.subprocess.run") as run_mock:
            run_mock.return_value = mock_subprocess_run_success("valid_atm_iv_spy")
            data = data_fetcher._fetch_atm_iv("SPY", expiration="2026-02-20")

        assert data is not None
        assert data["implied_volatility"] == 0.18
        assert data["is_atm"] is True

    def test_ibkr_iv_warning_not_atm(self):
        with patch("data_fetcher.subprocess.run") as run_mock:
            run_mock.return_value = mock_subprocess_run_success("invalid_iv_not_atm")
            data = data_fetcher._fetch_atm_iv("QQQ", expiration="2026-04-17")

        assert data is not None
        assert data["is_atm"] is False

    def test_ibkr_iv_no_options_data(self):
        class MockCompletedProcess:
            def __init__(self):
                self.stdout = '{"ticker": "SPY", "implied_volatility": null}'
                self.stderr = ""
                self.returncode = 0

        with patch("data_fetcher.subprocess.run", return_value=MockCompletedProcess()):
            data = data_fetcher._fetch_atm_iv("SPY", expiration="2026-02-20")

        assert data is None

    def test_ibkr_iv_timeout(self):
        with patch("data_fetcher.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            data = data_fetcher._fetch_atm_iv("SPY", expiration="2026-02-20")

        assert data is None


class TestDeltaValidation:
    """Tests for delta ATM range validation."""

    def test_delta_atm_range(self):
        assert data_fetcher._is_atm_delta(0.40) is True
        assert data_fetcher._is_atm_delta(0.50) is True
        assert data_fetcher._is_atm_delta(0.60) is True

    def test_delta_otm(self):
        assert data_fetcher._is_atm_delta(0.25) is False

    def test_delta_itm(self):
        assert data_fetcher._is_atm_delta(0.75) is False
