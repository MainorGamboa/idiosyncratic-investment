"""
Data Quality Monitoring for Options Trading

Real-time validation of IBKR data to prevent trading on invalid responses.
Implements circuit breaker pattern: halt trading after 3 consecutive failures.

Usage:
    from data_quality_monitor import OptionsDataQualityMonitor

    monitor = OptionsDataQualityMonitor(config)
    valid, error = monitor.validate_greeks(greeks_dict)
    if not valid:
        monitor.record_failure("greeks_validation", error)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


class OptionsDataQualityMonitor:
    """
    Real-time data quality validation for options trading.

    Validates:
    - Greeks ranges (IV, delta, theta, gamma, vega)
    - Pricing sanity (bid/ask spread, crossed markets)
    - Liquidity thresholds (open interest, volume)

    Circuit breaker:
    - Triggers after 3 consecutive validation failures
    - Halts all options trading
    - Writes immediate alert to alerts.json
    - Requires manual reset
    """

    def __init__(self, config: Dict):
        """
        Initialize monitor with config thresholds.

        Args:
            config: CONFIG.json data with data_quality settings
        """
        self.config = config
        self.failures = []
        self.circuit_breaker_triggered = False

        # Load thresholds from config
        dq_config = config.get("data_quality", {})

        self.greeks_validation = dq_config.get("greeks_validation", {
            "iv_range": [0.10, 3.00],
            "delta_range_calls": [0.01, 1.00],
            "theta_range_long": [-10.0, 0.0],
            "gamma_range": [0.0, 1.0],
            "vega_range": [0.0, 10.0]
        })

        self.pricing_validation = dq_config.get("pricing_validation", {
            "max_bid_ask_spread_pct": 0.15,
            "min_bid": 0.01,
            "min_ask": 0.01
        })

        self.liquidity_validation = dq_config.get("liquidity_validation", {
            "min_open_interest": 50,
            "min_daily_volume": 10
        })

        self.circuit_breaker_config = dq_config.get("circuit_breaker", {
            "consecutive_failures_threshold": 3,
            "timeout_threshold_per_hour": 3,
            "auto_reset_after_hours": 24
        })

    def validate_greeks(self, greeks: Dict, right: str = "CALL") -> Tuple[bool, str]:
        """
        Validate Greeks are within expected ranges.

        Args:
            greeks: Dict with delta, theta, gamma, vega, implied_volatility
            right: "CALL" or "PUT"

        Returns:
            Tuple of (is_valid, error_message)
        """
        # IV: 10% to 300%
        iv = greeks.get("implied_volatility")
        if iv is not None:
            iv_min, iv_max = self.greeks_validation["iv_range"]
            if not (iv_min <= iv <= iv_max):
                return False, f"IV {iv*100:.1f}% outside range [{iv_min*100:.0f}%, {iv_max*100:.0f}%]"

        # Delta for calls: 0.01 to 1.00
        delta = greeks.get("delta")
        if delta is not None and right == "CALL":
            delta_min, delta_max = self.greeks_validation["delta_range_calls"]
            if not (delta_min <= delta <= delta_max):
                return False, f"Delta {delta:.3f} outside range [{delta_min}, {delta_max}]"

        # Theta should be negative for long calls (time decay)
        theta = greeks.get("theta")
        if theta is not None and right == "CALL":
            theta_min, theta_max = self.greeks_validation["theta_range_long"]
            if not (theta_min <= theta <= theta_max):
                return False, f"Theta {theta:.3f} outside range [{theta_min}, {theta_max}]"

            # Positive theta is especially suspicious for long options
            if theta > 0:
                return False, f"Theta {theta:.3f} is positive (expected negative for long calls)"

        # Gamma should be positive and reasonable
        gamma = greeks.get("gamma")
        if gamma is not None:
            gamma_min, gamma_max = self.greeks_validation["gamma_range"]
            if not (gamma_min < gamma <= gamma_max):
                return False, f"Gamma {gamma:.4f} outside range ({gamma_min}, {gamma_max}]"

        # Vega should be positive
        vega = greeks.get("vega")
        if vega is not None:
            vega_min, vega_max = self.greeks_validation["vega_range"]
            if not (vega_min < vega <= vega_max):
                return False, f"Vega {vega:.4f} outside range ({vega_min}, {vega_max}]"

        # Check that we have at least delta, theta, and IV
        critical_greeks = [greeks.get("delta"), greeks.get("theta"), greeks.get("implied_volatility")]
        valid_critical = sum(1 for g in critical_greeks if g is not None)

        if valid_critical < 3:
            return False, f"Missing critical Greeks (have {valid_critical}/3: delta, theta, IV)"

        return True, ""

    def validate_pricing(self, bid: Optional[float], ask: Optional[float], last: Optional[float]) -> Tuple[bool, str]:
        """
        Validate bid/ask pricing is reasonable.

        Args:
            bid: Bid price
            ask: Ask price
            last: Last traded price

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check bid and ask exist
        if bid is None or ask is None:
            return False, "Missing bid or ask price"

        # Check positive prices
        min_bid = self.pricing_validation["min_bid"]
        min_ask = self.pricing_validation["min_ask"]

        if bid <= 0 or ask <= 0:
            return False, f"Invalid prices: bid={bid}, ask={ask} (must be positive)"

        if bid < min_bid:
            return False, f"Bid {bid:.2f} below minimum {min_bid}"

        if ask < min_ask:
            return False, f"Ask {ask:.2f} below minimum {min_ask}"

        # Check for crossed market (bid > ask is data error)
        if bid > ask:
            return False, f"Crossed market: bid {bid:.2f} > ask {ask:.2f}"

        # Bid-ask spread check
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid if mid > 0 else 999
        max_spread = self.pricing_validation["max_bid_ask_spread_pct"]

        if spread_pct > max_spread:
            return False, f"Wide spread: {spread_pct*100:.1f}% (max {max_spread*100:.0f}%)"

        return True, ""

    def validate_liquidity(self, open_interest: Optional[int], volume: Optional[int]) -> Tuple[bool, str]:
        """
        Validate sufficient liquidity.

        Note: This returns warnings but doesn't trigger circuit breaker.
        Low liquidity = can't trade, but not a data quality issue.

        Args:
            open_interest: Open interest
            volume: Daily volume

        Returns:
            Tuple of (is_valid, warning_message)
        """
        min_oi = self.liquidity_validation["min_open_interest"]
        min_vol = self.liquidity_validation["min_daily_volume"]

        if open_interest is None or open_interest < min_oi:
            return False, f"Low open interest: {open_interest} (min {min_oi})"

        if volume is not None and volume < min_vol:
            # Volume warning is less critical - options can have low volume with good OI
            return False, f"Low volume: {volume} (min {min_vol})"

        return True, ""

    def record_failure(self, failure_type: str, error: str, ticker: Optional[str] = None):
        """
        Record a data quality failure.

        Args:
            failure_type: Type of failure (greeks_validation, pricing_validation, etc.)
            error: Error message
            ticker: Optional ticker symbol
        """
        failure = {
            "timestamp": datetime.now().isoformat(),
            "type": failure_type,
            "error": error,
            "ticker": ticker
        }

        self.failures.append(failure)

        # Log to daily data quality log
        self._log_failure(failure)

        # Check if we should trigger circuit breaker
        consecutive_failures = len(self.failures)
        threshold = self.circuit_breaker_config["consecutive_failures_threshold"]

        if consecutive_failures >= threshold and not self.circuit_breaker_triggered:
            self.trigger_circuit_breaker(
                f"{consecutive_failures} consecutive data quality failures. Latest: {error}"
            )

    def reset_failures(self):
        """Reset failure counter on successful validation."""
        self.failures = []

    def trigger_circuit_breaker(self, reason: str):
        """
        Halt all options trading and send immediate alert.

        Args:
            reason: Reason for triggering circuit breaker
        """
        if self.circuit_breaker_triggered:
            # Already triggered, don't duplicate
            return

        self.circuit_breaker_triggered = True

        alert_id = f"alert-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        alert = {
            "id": alert_id,
            "timestamp": datetime.now().isoformat(),
            "priority": "immediate",
            "type": "circuit_breaker",
            "subsystem": "options_data_quality",
            "reason": reason,
            "action_required": "Review logs/data_quality/ and manually reset circuit breaker",
            "acknowledged": False,
            "failures": self.failures[-10:]  # Last 10 failures
        }

        # Write to alerts.json
        self._write_alert(alert)

        # Log circuit breaker event
        self._log_circuit_breaker(reason)

        # Raise exception to halt execution
        raise RuntimeError(f"⛔ OPTIONS TRADING HALTED: {reason}")

    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently triggered."""
        return self.circuit_breaker_triggered

    def reset_circuit_breaker(self):
        """
        Manually reset circuit breaker (requires user intervention).

        Should only be called after reviewing logs and confirming data quality is restored.
        """
        self.circuit_breaker_triggered = False
        self.failures = []

        # Log reset
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "circuit_breaker_reset",
            "note": "Manual reset by user"
        }

        self._log_circuit_breaker_reset(log_entry)

    def _write_alert(self, alert: Dict):
        """Write alert to alerts.json."""
        alerts_file = Path("alerts.json")

        try:
            if alerts_file.exists():
                alerts_data = json.loads(alerts_file.read_text())
            else:
                alerts_data = {
                    "alerts": [],
                    "metadata": {
                        "version": "1.0",
                        "description": "Active alerts requiring user action"
                    }
                }

            # Add new alert
            alerts_data["alerts"].append(alert)

            # Write back
            alerts_file.write_text(json.dumps(alerts_data, indent=2))

            print(f"\n⚠️  IMMEDIATE ALERT: {alert['reason']}", flush=True)
            print(f"Alert ID: {alert['id']}", flush=True)
            print(f"Review: alerts.json", flush=True)

        except Exception as e:
            print(f"ERROR: Could not write alert to alerts.json: {e}", flush=True)

    def _log_failure(self, failure: Dict):
        """Log failure to daily data quality log."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = Path(f"logs/data_quality/{today}.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if log_file.exists():
                log_data = json.loads(log_file.read_text())
            else:
                log_data = {
                    "date": today,
                    "events": []
                }

            log_data["events"].append({
                "type": "validation_failure",
                **failure
            })

            log_file.write_text(json.dumps(log_data, indent=2))
        except Exception as e:
            print(f"WARNING: Could not write to data quality log: {e}", flush=True)

    def _log_circuit_breaker(self, reason: str):
        """Log circuit breaker trigger event."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = Path(f"logs/data_quality/{today}.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if log_file.exists():
                log_data = json.loads(log_file.read_text())
            else:
                log_data = {
                    "date": today,
                    "events": []
                }

            log_data["events"].append({
                "type": "circuit_breaker_triggered",
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "failures_count": len(self.failures)
            })

            log_file.write_text(json.dumps(log_data, indent=2))
        except Exception as e:
            print(f"WARNING: Could not write circuit breaker event: {e}", flush=True)

    def _log_circuit_breaker_reset(self, log_entry: Dict):
        """Log circuit breaker reset event."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = Path(f"logs/data_quality/{today}.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if log_file.exists():
                log_data = json.loads(log_file.read_text())
            else:
                log_data = {
                    "date": today,
                    "events": []
                }

            log_data["events"].append({
                "type": "circuit_breaker_reset",
                **log_entry
            })

            log_file.write_text(json.dumps(log_data, indent=2))
        except Exception as e:
            print(f"WARNING: Could not write circuit breaker reset: {e}", flush=True)


def load_config() -> Dict:
    """Load CONFIG.json."""
    config_path = Path(__file__).resolve().parents[1] / "CONFIG.json"
    with open(config_path, "r") as f:
        return json.load(f)


# Module-level singleton for easy import
_monitor_instance = None


def get_monitor() -> OptionsDataQualityMonitor:
    """
    Get singleton instance of monitor.

    Returns:
        Shared OptionsDataQualityMonitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        config = load_config()
        _monitor_instance = OptionsDataQualityMonitor(config)
    return _monitor_instance


if __name__ == "__main__":
    # Test the monitor
    monitor = get_monitor()

    # Test valid Greeks
    greeks = {
        "delta": 0.52,
        "theta": -0.03,
        "gamma": 0.02,
        "vega": 0.15,
        "implied_volatility": 0.25
    }

    valid, error = monitor.validate_greeks(greeks)
    print(f"Valid Greeks: {valid}")
    if not valid:
        print(f"Error: {error}")

    # Test invalid IV
    bad_greeks = {
        "delta": 0.52,
        "theta": -0.03,
        "implied_volatility": 4.50  # 450% - too high
    }

    valid, error = monitor.validate_greeks(bad_greeks)
    print(f"\nInvalid Greeks (high IV): {valid}")
    if not valid:
        print(f"Error: {error}")
