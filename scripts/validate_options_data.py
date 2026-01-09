#!/usr/bin/env python3
"""
Daily Options Data Quality Validation Script

Run this script daily for 1 week to validate IBKR integration and data quality.

Usage:
    python scripts/validate_options_data.py

Output:
    - Console: Test results summary
    - File: logs/data_quality/YYYY-MM-DD.json

Exit codes:
    0: All tests passed
    1: One or more tests failed
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import fetch_options_data
from data_quality_monitor import get_monitor


class OptionsDataValidator:
    """Daily validation tests for IBKR options data quality."""

    def __init__(self):
        self.results = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": [],
            "tests": []
        }
        self.monitor = get_monitor()

    def run_all_tests(self):
        """Run all validation tests."""
        print(f"\nTesting IBKR Options Data Quality - {self.results['date']}")
        print("=" * 60)

        # Test 1: Fetch SPY call option (ATM, ~30 DTE)
        self.test_fetch_spy_option()

        # Test 2: Validate Greeks are within expected ranges
        self.test_greeks_validation()

        # Test 3: Test order preview (no execution)
        self.test_order_preview()

        # Test 4: Check bid-ask spread quality
        self.test_bid_ask_spreads()

        # Test 5: Verify IBKR connection latency
        self.test_connection_latency()

        # Print summary
        print("\n" + "=" * 60)
        if self.results["tests_failed"] > 0:
            print(f"❌ FAILED: {self.results['tests_failed']} tests failed")
            print(f"Review: logs/data_quality/{self.results['date']}.json")
            exit_code = 1
        else:
            print(f"✅ PASSED: All {self.results['tests_passed']} tests passed")
            exit_code = 0

        # Write results to log
        self.write_log()

        return exit_code

    def test_fetch_spy_option(self):
        """Test 1: Fetch SPY ATM call option (~30 DTE)."""
        test_name = "SPY call option fetch"
        print(f"\nRunning: {test_name}")

        try:
            start_time = time.time()

            # Calculate ~30 DTE expiration (next monthly expiration)
            today = datetime.now()
            # Find next monthly expiration (3rd Friday of next month)
            next_month = today + timedelta(days=30)
            # Simplified: just use a date ~30 days out
            expiration = (today + timedelta(days=30)).strftime('%Y-%m-%d')

            # Fetch SPY option (using current price as strike approximation)
            options_data = fetch_options_data("SPY", 500.0, expiration)

            elapsed = time.time() - start_time

            if options_data and options_data.get("data_quality_validated"):
                self.record_pass(test_name, f"({elapsed:.1f}s)", {
                    "ticker": "SPY",
                    "strike": 500.0,
                    "expiration": expiration,
                    "mid_price": options_data.get("mid_price"),
                    "delta": options_data.get("delta"),
                    "iv": options_data.get("implied_volatility"),
                    "elapsed_seconds": elapsed
                })
            else:
                self.record_fail(test_name, "Failed to fetch SPY option or validation failed", {
                    "expiration": expiration
                })

        except Exception as e:
            self.record_fail(test_name, str(e))

    def test_greeks_validation(self):
        """Test 2: Validate Greeks are within expected ranges."""
        test_name = "Greeks validation"
        print(f"\nRunning: {test_name}")

        try:
            # Use the data from test 1 if available
            last_test = self.results["tests"][-1] if self.results["tests"] else None

            if last_test and last_test["status"] == "passed":
                delta = last_test["details"].get("delta")
                iv = last_test["details"].get("iv")

                # Check ranges
                if delta and 0.01 <= delta <= 1.00:
                    delta_ok = True
                else:
                    delta_ok = False

                if iv and 0.10 <= iv <= 3.00:
                    iv_ok = True
                else:
                    iv_ok = False

                if delta_ok and iv_ok:
                    self.record_pass(test_name, f"(delta={delta:.2f}, IV={iv*100:.1f}%)", {
                        "delta": delta,
                        "delta_range": [0.01, 1.00],
                        "iv": iv,
                        "iv_range": [0.10, 3.00]
                    })
                else:
                    self.record_fail(test_name, "Greeks outside expected ranges", {
                        "delta": delta,
                        "delta_ok": delta_ok,
                        "iv": iv,
                        "iv_ok": iv_ok
                    })
            else:
                self.record_fail(test_name, "No data from previous test")

        except Exception as e:
            self.record_fail(test_name, str(e))

    def test_order_preview(self):
        """Test 3: Test order preview generation (no execution)."""
        test_name = "Order preview generation"
        print(f"\nRunning: {test_name}")

        try:
            # Import here to avoid circular dependency
            from order_manager import preview_options_order

            # Use data from test 1
            last_test = self.results["tests"][0] if len(self.results["tests"]) > 0 else None

            if last_test and last_test["status"] == "passed":
                details = last_test["details"]

                # Create preview (1 contract, small position)
                preview = preview_options_order(
                    ticker="SPY",
                    strike=details["strike"],
                    expiration=details["expiration"],
                    contracts=1,
                    archetype="test",
                    right="CALL",
                    options_strategy="long_calls",
                    score=8.0,
                    kill_screens="PASS"
                )

                if preview and preview.total_premium > 0:
                    self.record_pass(test_name, "", {
                        "preview_id": preview.preview_id,
                        "contracts": preview.contracts,
                        "total_premium": preview.total_premium,
                        "leverage_ratio": preview.leverage_ratio
                    })
                else:
                    self.record_fail(test_name, "Preview generation failed or invalid")
            else:
                self.record_fail(test_name, "No data from test 1")

        except Exception as e:
            self.record_fail(test_name, str(e))

    def test_bid_ask_spreads(self):
        """Test 4: Check bid-ask spread quality."""
        test_name = "Bid-ask spread check"
        print(f"\nRunning: {test_name}")

        try:
            last_test = self.results["tests"][0] if len(self.results["tests"]) > 0 else None

            if last_test and last_test["status"] == "passed":
                # Get bid/ask from first test
                expiration = last_test["details"]["expiration"]
                options_data = fetch_options_data("SPY", 500.0, expiration)

                if options_data:
                    bid = options_data.get("bid")
                    ask = options_data.get("ask")

                    if bid and ask:
                        mid = (bid + ask) / 2
                        spread_pct = (ask - bid) / mid if mid > 0 else 999

                        if spread_pct <= 0.15:  # 15% threshold
                            self.record_pass(test_name, f"({spread_pct*100:.1f}% of mid)", {
                                "bid": bid,
                                "ask": ask,
                                "mid": mid,
                                "spread_pct": spread_pct
                            })
                        else:
                            self.record_fail(test_name, f"Wide spread: {spread_pct*100:.1f}%", {
                                "bid": bid,
                                "ask": ask,
                                "spread_pct": spread_pct
                            })
                    else:
                        self.record_fail(test_name, "Missing bid or ask")
                else:
                    self.record_fail(test_name, "Failed to fetch options data")
            else:
                self.record_fail(test_name, "No data from test 1")

        except Exception as e:
            self.record_fail(test_name, str(e))

    def test_connection_latency(self):
        """Test 5: Verify IBKR connection latency < 5s."""
        test_name = "Connection latency"
        print(f"\nRunning: {test_name}")

        try:
            start_time = time.time()

            # Quick fetch to measure latency
            expiration = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            options_data = fetch_options_data("SPY", 500.0, expiration)

            elapsed = time.time() - start_time

            if elapsed < 5.0:
                self.record_pass(test_name, f"({elapsed:.1f}s)", {
                    "elapsed_seconds": elapsed,
                    "threshold_seconds": 5.0
                })
            else:
                self.record_fail(test_name, f"Latency too high: {elapsed:.1f}s", {
                    "elapsed_seconds": elapsed,
                    "threshold_seconds": 5.0
                })

        except Exception as e:
            self.record_fail(test_name, str(e))

    def record_pass(self, test_name, note="", details=None):
        """Record a passing test."""
        print(f"✓ {test_name} {note}")
        self.results["tests_passed"] += 1
        self.results["tests"].append({
            "name": test_name,
            "status": "passed",
            "timestamp": datetime.now().isoformat(),
            "note": note,
            "details": details or {}
        })

    def record_fail(self, test_name, error, details=None):
        """Record a failing test."""
        print(f"✗ {test_name}: {error}")
        self.results["tests_failed"] += 1
        self.results["failures"].append({
            "test": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.results["tests"].append({
            "name": test_name,
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "details": details or {}
        })

    def write_log(self):
        """Write results to daily log file."""
        log_dir = Path("logs/data_quality")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{self.results['date']}.json"

        # If file exists, append to events
        if log_file.exists():
            existing_data = json.loads(log_file.read_text())
        else:
            existing_data = {
                "date": self.results['date'],
                "events": []
            }

        # Add this validation run as an event
        existing_data["events"].append({
            "type": "daily_validation",
            **self.results
        })

        log_file.write_text(json.dumps(existing_data, indent=2))

        print(f"\nResults logged to: {log_file}")


def main():
    """Main entry point."""
    validator = OptionsDataValidator()
    exit_code = validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
