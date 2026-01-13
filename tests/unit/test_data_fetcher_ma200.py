"""
Unit tests for MA-200 market data fetching and calculation.
"""

import sys
from pathlib import Path
from unittest.mock import patch
import subprocess

# Add scripts and fixtures directories to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))

import data_fetcher
import price_sources
from ibkr_fixtures import mock_subprocess_run_success


class TestMA200Calculation:
    """Tests for MA-200 calculation logic."""

    def test_ma200_calculation_exact_200_bars(self):
        bars = [{"close": value} for value in range(1, 201)]
        ma_200 = data_fetcher._calculate_ma_200(bars)
        assert ma_200 == 100.5

    def test_ma200_calculation_more_than_200_bars(self):
        bars = [{"close": value} for value in range(1, 206)]
        ma_200 = data_fetcher._calculate_ma_200(bars)
        assert ma_200 == 105.5

    def test_ma200_insufficient_bars(self):
        bars = [{"close": value} for value in range(1, 200)]
        ma_200 = data_fetcher._calculate_ma_200(bars)
        assert ma_200 is None


class TestIBKRHistoricalFetch:
    """Tests for IBKR historical fetch handling."""

    def test_ibkr_historical_success(self):
        with patch("data_fetcher.subprocess.run") as run_mock, patch(
            "data_fetcher.fetch_historical_yahoo"
        ) as yahoo_mock:
            run_mock.return_value = mock_subprocess_run_success("valid_historical_data_spy")
            data = data_fetcher._fetch_ma_200("SPY")

        assert data is not None
        assert data["source"] == "IBKR Paper"
        assert data["bars_used"] == 200
        assert data["bars_total"] == 205
        yahoo_mock.assert_not_called()

    def test_ibkr_historical_insufficient_bars(self):
        yahoo_bars = [
            {"date": f"2026-01-{idx:02d}", "close": float(idx), "volume": 100}
            for idx in range(1, 211)
        ]
        with patch("data_fetcher.subprocess.run") as run_mock, patch(
            "data_fetcher.fetch_historical_yahoo",
            return_value=yahoo_bars,
        ) as yahoo_mock:
            run_mock.return_value = mock_subprocess_run_success("insufficient_historical_data")
            data = data_fetcher._fetch_ma_200("NEWIPO")

        assert data is not None
        assert data["source"] == "Yahoo Finance"
        assert data["bars_used"] == 200
        yahoo_mock.assert_called_once()

    def test_ibkr_historical_timeout(self):
        yahoo_bars = [
            {"date": f"2026-02-{idx:02d}", "close": float(idx), "volume": 100}
            for idx in range(1, 211)
        ]
        with patch("data_fetcher.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            with patch("data_fetcher.fetch_historical_yahoo", return_value=yahoo_bars):
                data = data_fetcher._fetch_ma_200("SPY")

        assert data is not None
        assert data["source"] == "Yahoo Finance"


class TestYahooHistoricalFallback:
    """Tests for Yahoo Finance historical fallback."""

    def test_yahoo_historical_success(self):
        payload = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1700000000, 1700086400],
                        "indicators": {
                            "quote": [
                                {"close": [100.0, 101.0], "volume": [1000, 1100]}
                            ]
                        },
                    }
                ]
            }
        }

        class MockResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        with patch("price_sources.requests.get", return_value=MockResponse()):
            bars = price_sources.fetch_historical_yahoo("SPY", days=2)

        assert bars is not None
        assert len(bars) == 2
        assert bars[0]["close"] == 100.0
        assert bars[1]["volume"] == 1100

    def test_yahoo_historical_filter_none_values(self):
        payload = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1700000000, 1700086400, 1700172800],
                        "indicators": {
                            "quote": [
                                {"close": [100.0, None, 102.0], "volume": [1000, 0, 1200]}
                            ]
                        },
                    }
                ]
            }
        }

        class MockResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        with patch("price_sources.requests.get", return_value=MockResponse()):
            bars = price_sources.fetch_historical_yahoo("SPY", days=3)

        assert bars is not None
        assert len(bars) == 2
        assert all(bar["close"] is not None for bar in bars)


class TestNextMonthlyExpiration:
    """Tests for next monthly expiration calculation."""

    def test_calculate_next_monthly_expiration(self, monkeypatch):
        class FixedDate(data_fetcher.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 10)

        monkeypatch.setattr(data_fetcher, "datetime", FixedDate)
        assert data_fetcher._calculate_next_monthly_expiration() == "2026-01-16"

    def test_expiration_is_future(self, monkeypatch):
        class FixedDate(data_fetcher.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 20)

        monkeypatch.setattr(data_fetcher, "datetime", FixedDate)
        assert data_fetcher._calculate_next_monthly_expiration() == "2026-02-20"
