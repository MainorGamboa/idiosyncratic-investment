"""
Mock IBKR responses for testing without live broker connection.

Provides realistic responses for:
- Valid Greeks data
- Invalid Greeks (None values, sentinels)
- Timeout errors
- Malformed JSON
"""

import json


class IBKRMockResponses:
    """Mock IBKR API responses for testing."""

    @staticmethod
    def valid_spy_call_atm():
        """Valid SPY ATM call option with all Greeks."""
        return {
            "ticker": "SPY",
            "strike": 500.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 9.50,
            "ask": 9.70,
            "last": 9.60,
            "mid_price": 9.60,
            "delta": 0.52,
            "theta": -0.03,
            "gamma": 0.02,
            "vega": 0.15,
            "implied_volatility": 0.18,  # 18% IV
            "open_interest": 15000,
            "volume": 3500,
            "underlying_price": 500.25,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def valid_aapl_call_itm():
        """Valid AAPL ITM call option (delta ~0.70)."""
        return {
            "ticker": "AAPL",
            "strike": 175.0,
            "expiration": "2026-03-20",
            "right": "CALL",
            "bid": 15.20,
            "ask": 15.50,
            "last": 15.35,
            "mid_price": 15.35,
            "delta": 0.72,
            "theta": -0.05,
            "gamma": 0.015,
            "vega": 0.25,
            "implied_volatility": 0.25,  # 25% IV
            "open_interest": 8500,
            "volume": 1200,
            "underlying_price": 185.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def valid_qqq_call_otm():
        """Valid QQQ OTM call option (delta ~0.30)."""
        return {
            "ticker": "QQQ",
            "strike": 420.0,
            "expiration": "2026-04-17",
            "right": "CALL",
            "bid": 2.80,
            "ask": 2.95,
            "last": 2.88,
            "mid_price": 2.88,
            "delta": 0.32,
            "theta": -0.02,
            "gamma": 0.025,
            "vega": 0.18,
            "implied_volatility": 0.22,  # 22% IV
            "open_interest": 12000,
            "volume": 4500,
            "underlying_price": 405.75,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_greeks_none_values():
        """IBKR response with None values for Greeks."""
        return {
            "ticker": "XYZ",
            "strike": 100.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 5.00,
            "ask": 5.20,
            "last": 5.10,
            "mid_price": 5.10,
            "delta": None,           # Missing
            "theta": None,           # Missing
            "gamma": None,           # Missing
            "vega": None,            # Missing
            "implied_volatility": None,  # Missing
            "open_interest": 500,
            "volume": 50,
            "underlying_price": 100.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_greeks_sentinel_values():
        """IBKR response with -1/-2 sentinel values."""
        return {
            "ticker": "ABC",
            "strike": 50.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 2.00,
            "ask": 2.10,
            "last": 2.05,
            "mid_price": 2.05,
            "delta": -1,             # IBKR sentinel
            "theta": -2,             # IBKR sentinel
            "gamma": -1,             # IBKR sentinel
            "vega": -2,              # IBKR sentinel
            "implied_volatility": -1,  # IBKR sentinel
            "open_interest": 200,
            "volume": 10,
            "underlying_price": 50.25,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_iv_too_high():
        """Option with suspiciously high IV (>300%)."""
        return {
            "ticker": "MEME",
            "strike": 10.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 8.50,
            "ask": 9.00,
            "last": 8.75,
            "mid_price": 8.75,
            "delta": 0.55,
            "theta": -0.10,
            "gamma": 0.08,
            "vega": 0.50,
            "implied_volatility": 4.50,  # 450% IV - invalid
            "open_interest": 1000,
            "volume": 500,
            "underlying_price": 10.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_wide_spread():
        """Option with wide bid-ask spread (>15%)."""
        return {
            "ticker": "ILLIQ",
            "strike": 25.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 1.00,
            "ask": 1.50,             # 50% spread - too wide
            "last": 1.20,
            "mid_price": 1.25,
            "delta": 0.45,
            "theta": -0.02,
            "gamma": 0.03,
            "vega": 0.10,
            "implied_volatility": 0.40,
            "open_interest": 25,     # Low OI
            "volume": 2,             # Low volume
            "underlying_price": 25.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_low_liquidity():
        """Option with low open interest (<50)."""
        return {
            "ticker": "LOWOI",
            "strike": 75.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 3.00,
            "ask": 3.10,
            "last": 3.05,
            "mid_price": 3.05,
            "delta": 0.50,
            "theta": -0.03,
            "gamma": 0.02,
            "vega": 0.15,
            "implied_volatility": 0.30,
            "open_interest": 15,     # Below 50 threshold
            "volume": 5,
            "underlying_price": 75.25,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def invalid_crossed_market():
        """Bid > Ask (crossed market - data error)."""
        return {
            "ticker": "ERROR",
            "strike": 100.0,
            "expiration": "2026-02-20",
            "right": "CALL",
            "bid": 5.50,             # Bid > Ask (error)
            "ask": 5.00,
            "last": 5.25,
            "mid_price": 5.25,
            "delta": 0.52,
            "theta": -0.03,
            "gamma": 0.02,
            "vega": 0.15,
            "implied_volatility": 0.20,
            "open_interest": 1000,
            "volume": 100,
            "underlying_price": 100.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def timeout_error():
        """Simulate IBKR timeout."""
        return {
            "error": "timeout",
            "message": "IBKR connection timeout after 30 seconds"
        }

    @staticmethod
    def malformed_json():
        """Simulate malformed JSON response."""
        return '{"ticker": "SPY", "strike": 500.0, "delta": INVALID_VALUE}'

    @staticmethod
    def connection_refused():
        """Simulate IBKR connection refused."""
        return {
            "error": "connection_refused",
            "message": "Could not connect to IBKR at 127.0.0.1:4002"
        }

    @staticmethod
    def high_iv_biotech_valid():
        """Biotech option with high but valid IV (150%)."""
        return {
            "ticker": "SRPT",
            "strike": 125.0,
            "expiration": "2026-03-15",
            "right": "CALL",
            "bid": 8.00,
            "ask": 8.50,
            "last": 8.25,
            "mid_price": 8.25,
            "delta": 0.48,
            "theta": -0.08,
            "gamma": 0.025,
            "vega": 0.35,
            "implied_volatility": 1.50,  # 150% IV - high but valid for PDUFA biotech
            "open_interest": 500,
            "volume": 150,
            "underlying_price": 125.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }

    @staticmethod
    def leaps_call_valid():
        """LEAPS call (18 months out) with typical Greeks."""
        return {
            "ticker": "ABBV",
            "strike": 175.0,
            "expiration": "2027-07-16",  # 18 months
            "right": "CALL",
            "bid": 22.00,
            "ask": 22.50,
            "last": 22.25,
            "mid_price": 22.25,
            "delta": 0.58,
            "theta": -0.01,          # Lower theta for LEAPS
            "gamma": 0.008,          # Lower gamma for LEAPS
            "vega": 0.40,            # Higher vega for LEAPS
            "implied_volatility": 0.28,
            "open_interest": 2500,
            "volume": 350,
            "underlying_price": 177.50,
            "timestamp": "2026-01-08T14:30:00Z",
            "source": "IBKR Paper"
        }


def get_mock_response(response_type: str):
    """
    Get mock IBKR response by type.

    Args:
        response_type: Type of response (e.g., 'valid_spy_call_atm', 'invalid_greeks_none_values')

    Returns:
        Dict or str with mock response
    """
    responses = IBKRMockResponses()

    if hasattr(responses, response_type):
        return getattr(responses, response_type)()
    else:
        raise ValueError(f"Unknown response type: {response_type}")


def mock_subprocess_run_success(response_type: str):
    """
    Create a mock subprocess.run() result for successful IBKR call.

    Args:
        response_type: Type of mock response

    Returns:
        Mock CompletedProcess object
    """
    class MockCompletedProcess:
        def __init__(self, stdout, stderr, returncode):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    response_data = get_mock_response(response_type)

    # Handle special cases
    if response_type == "malformed_json":
        return MockCompletedProcess(
            stdout=response_data,  # Already a malformed string
            stderr="",
            returncode=0
        )

    if response_type == "timeout_error":
        raise TimeoutError("IBKR timeout")

    if response_type == "connection_refused":
        return MockCompletedProcess(
            stdout="",
            stderr="Connection refused",
            returncode=1
        )

    # Normal response
    return MockCompletedProcess(
        stdout=json.dumps(response_data),
        stderr="",
        returncode=0
    )


def mock_subprocess_run_failure():
    """Create a mock subprocess.run() result for failed IBKR call."""
    class MockCompletedProcess:
        def __init__(self, stdout, stderr, returncode):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    return MockCompletedProcess(
        stdout="",
        stderr="IBKR error: Invalid contract",
        returncode=1
    )
