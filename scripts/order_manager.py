"""
Order Manager Module

Handles order preview, confirmation, and execution for paper trading.
Provides semi-automated workflow with user approval before execution.

Features:
- Order preview with formatted display
- User confirmation prompt
- IBKR integration for execution
- Order logging
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

from price_sources import get_bid_ask_midpoint


@dataclass
class OrderPreview:
    """Container for order preview information."""
    ticker: str
    action: str  # BUY or SELL
    shares: int
    order_type: str  # LMT or MKT
    limit_price: Optional[float]  # For limit orders
    total_cost: float
    position_size_pct: float
    account_size: float

    # Rationale
    archetype: str
    score: Optional[float]
    kill_screens: str
    catalyst_date: Optional[str]
    entry_timing: Optional[str]

    # Risk management
    max_loss: float
    stop_price: Optional[float]

    # Metadata
    timestamp: str
    preview_id: str


def load_config() -> Dict:
    """Load CONFIG.json."""
    config_path = Path(__file__).resolve().parents[1] / "CONFIG.json"

    with open(config_path, "r") as f:
        return json.load(f)


def calculate_position_size(account_size: float, max_loss_pct: float,
                            entry_price: float, stop_price: float,
                            archetype_max_pct: float) -> int:
    """
    Calculate position size using Kellner Rule (max 2% loss per trade).

    Args:
        account_size: Total account value
        max_loss_pct: Max loss as fraction (e.g., 0.02 for 2%)
        entry_price: Entry price per share
        stop_price: Stop loss price
        archetype_max_pct: Max position size for archetype (e.g., 0.015 for PDUFA)

    Returns:
        Number of shares to buy
    """
    # Kellner rule: max_loss_pct * account_size = (entry_price - stop_price) * shares
    max_loss_dollars = account_size * max_loss_pct
    risk_per_share = entry_price - stop_price

    if risk_per_share <= 0:
        return 0

    kellner_shares = int(max_loss_dollars / risk_per_share)

    # Apply archetype position cap
    archetype_max_shares = int((account_size * archetype_max_pct) / entry_price)

    # Return the minimum (most conservative)
    shares = min(kellner_shares, archetype_max_shares)

    return max(shares, 0)  # Ensure non-negative


def preview_order(ticker: str, action: str, shares: int,
                 archetype: str, score: Optional[float] = None,
                 kill_screens: str = "PASS",
                 catalyst_date: Optional[str] = None,
                 entry_timing: Optional[str] = None) -> OrderPreview:
    """
    Create order preview with all details.

    Args:
        ticker: Stock ticker
        action: BUY or SELL
        shares: Number of shares
        archetype: Trade archetype (pdufa, merger_arb, etc.)
        score: Total score from scoring filter
        kill_screens: Kill screen status
        catalyst_date: Catalyst date if applicable
        entry_timing: Entry timing assessment

    Returns:
        OrderPreview object
    """
    config = load_config()
    account_size = config["account"]["size"]

    # Get current price (bid/ask midpoint for limit orders)
    midpoint = get_bid_ask_midpoint(ticker)

    if not midpoint:
        raise ValueError(f"Could not get price for {ticker}")

    # Calculate costs
    total_cost = midpoint * shares
    position_size_pct = (total_cost / account_size) * 100

    # Calculate stop price (example: -24% for PDUFA)
    # TODO: Make this configurable per archetype
    stop_pct = 0.24
    stop_price = midpoint * (1 - stop_pct) if action == "BUY" else None

    # Calculate max loss
    max_loss = config["risk"]["max_loss_per_trade"] * account_size

    preview = OrderPreview(
        ticker=ticker.upper(),
        action=action.upper(),
        shares=shares,
        order_type="LMT",  # Default to limit orders
        limit_price=midpoint,
        total_cost=total_cost,
        position_size_pct=position_size_pct,
        account_size=account_size,
        archetype=archetype,
        score=score,
        kill_screens=kill_screens,
        catalyst_date=catalyst_date,
        entry_timing=entry_timing,
        max_loss=max_loss,
        stop_price=stop_price,
        timestamp=datetime.now().isoformat(),
        preview_id=f"{ticker}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )

    return preview


def display_preview(preview: OrderPreview):
    """
    Display formatted order preview to user.

    Args:
        preview: OrderPreview object
    """
    print()
    print("═" * 60)
    print(f"ORDER PREVIEW: {preview.action} {preview.ticker}")
    print("═" * 60)
    print(f"Ticker:           {preview.ticker}")
    print(f"Action:           {preview.action}")
    print(f"Shares:           {preview.shares}")
    print(f"Limit Price:      ${preview.limit_price:.2f} (bid/ask midpoint)")
    print(f"Total Cost:       ${preview.total_cost:,.2f}")
    print(f"Position Size:    {preview.position_size_pct:.2f}% of portfolio (${preview.account_size:,.0f})")
    print()
    print("Rationale:")
    print(f"  - Archetype: {preview.archetype.upper()}")
    if preview.score:
        print(f"  - Score: {preview.score:.1f} (BUY)")
    print(f"  - Kill screens: {preview.kill_screens}")
    if preview.catalyst_date:
        print(f"  - Catalyst date: {preview.catalyst_date}")
    if preview.entry_timing:
        print(f"  - Entry timing: {preview.entry_timing}")
    print()
    print(f"Max Loss (Kellner): ${preview.max_loss:,.0f} (2% of portfolio)")
    if preview.stop_price:
        stop_pct = ((preview.limit_price - preview.stop_price) / preview.limit_price) * 100
        print(f"Stop Price:         ${preview.stop_price:.2f} (-{stop_pct:.1f}% from entry)")
    print()
    print("═" * 60)


def get_user_confirmation() -> bool:
    """
    Prompt user for order confirmation.

    Returns:
        True if user confirms, False otherwise
    """
    while True:
        response = input("Execute this order? [y/N]: ").strip().lower()

        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no", ""]:
            return False
        else:
            print("Please enter 'y' or 'n'")


def execute_order(preview: OrderPreview, dry_run: bool = False) -> Dict:
    """
    Execute order via IBKR paper trading.

    Args:
        preview: OrderPreview object
        dry_run: If True, simulate without actual execution

    Returns:
        Dict with execution result
    """
    if dry_run:
        print("\n[DRY RUN MODE] Order simulated, not executed")
        return {
            "status": "SIMULATED",
            "order_id": "DRY-RUN-12345",
            "ticker": preview.ticker,
            "action": preview.action,
            "shares": preview.shares,
            "price": preview.limit_price,
            "dry_run": True
        }

    # Execute via IBKR script
    try:
        script_path = Path(__file__).parent / "ibkr_paper.py"

        cmd = [
            sys.executable,
            str(script_path),
            "place",
            preview.ticker,
            preview.action,
            str(preview.shares),
            "--order-type", preview.order_type
        ]

        if preview.limit_price:
            cmd.extend(["--limit", str(preview.limit_price)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return {
                "status": "FAILED",
                "error": result.stderr,
                "ticker": preview.ticker
            }

        # Parse IBKR response
        output = json.loads(result.stdout)

        return {
            "status": "EXECUTED",
            "order_id": output.get("order_id"),
            "ticker": preview.ticker,
            "action": preview.action,
            "shares": preview.shares,
            "price": preview.limit_price,
            "ibkr_response": output
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "error": "Order execution timed out",
            "ticker": preview.ticker
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "ticker": preview.ticker
        }


def log_order(preview: OrderPreview, execution_result: Dict):
    """
    Log order preview and execution to logs/orders/.

    Args:
        preview: OrderPreview object
        execution_result: Execution result dict
    """
    log_dir = Path(__file__).resolve().parents[1] / "logs" / "orders"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "preview": asdict(preview),
        "execution": execution_result
    }

    # Append to log file
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def main():
    """CLI interface for order management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage orders with preview and confirmation")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # preview command
    parser_preview = subparsers.add_parser("preview", help="Preview an order")
    parser_preview.add_argument("ticker", help="Stock ticker")
    parser_preview.add_argument("action", choices=["BUY", "SELL"], help="Order action")
    parser_preview.add_argument("shares", type=int, help="Number of shares")
    parser_preview.add_argument("--archetype", required=True, help="Trade archetype")
    parser_preview.add_argument("--score", type=float, help="Score from scoring filter")
    parser_preview.add_argument("--catalyst-date", help="Catalyst date")

    # execute command
    parser_execute = subparsers.add_parser("execute", help="Execute order with confirmation")
    parser_execute.add_argument("ticker", help="Stock ticker")
    parser_execute.add_argument("action", choices=["BUY", "SELL"], help="Order action")
    parser_execute.add_argument("shares", type=int, help="Number of shares")
    parser_execute.add_argument("--archetype", required=True, help="Trade archetype")
    parser_execute.add_argument("--score", type=float, help="Score from scoring filter")
    parser_execute.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    parser_execute.add_argument("--yes", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()
    dry_run = config.get("automation", {}).get("dry_run", False) or getattr(args, "dry_run", False)

    if args.command == "preview":
        preview = preview_order(
            args.ticker,
            args.action,
            args.shares,
            args.archetype,
            args.score,
            catalyst_date=getattr(args, "catalyst_date", None)
        )

        display_preview(preview)

    elif args.command == "execute":
        preview = preview_order(
            args.ticker,
            args.action,
            args.shares,
            args.archetype,
            args.score
        )

        display_preview(preview)

        # Get confirmation
        if not getattr(args, "yes", False):
            confirmed = get_user_confirmation()
            if not confirmed:
                print("\nOrder cancelled by user")
                sys.exit(0)

        # Execute
        print("\nExecuting order...")
        result = execute_order(preview, dry_run=dry_run)

        # Log
        log_order(preview, result)

        # Display result
        if result["status"] in ["EXECUTED", "SIMULATED"]:
            print(f"\n✓ Order {result['status'].lower()}: {result['ticker']} {preview.action} {preview.shares} shares")
            if "order_id" in result:
                print(f"  Order ID: {result['order_id']}")
        else:
            print(f"\n✗ Order failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
