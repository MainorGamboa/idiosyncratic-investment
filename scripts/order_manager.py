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
from typing import Union

from price_sources import get_bid_ask_midpoint
from data_fetcher import fetch_options_data


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


@dataclass
class OptionsOrderPreview:
    """Container for options order preview information."""
    ticker: str
    action: str  # BUY_CALL, BUY_PUT, etc.
    contracts: int
    strike: float
    expiration: str  # YYYY-MM-DD
    right: str  # CALL or PUT

    # Pricing
    premium_per_contract: float
    total_premium: float
    notional_exposure: float

    # Greeks
    delta: Optional[float]
    theta: Optional[float]  # Per day
    gamma: Optional[float]
    vega: Optional[float]
    implied_volatility: Optional[float]

    # Analysis
    breakeven_stock_price: float
    leverage_ratio: float  # notional / premium
    days_to_expiration: int

    # Portfolio context
    position_size_pct: float  # Premium as % of portfolio
    notional_pct: float  # Notional as % of portfolio
    account_size: float

    # Rationale
    archetype: str
    score: Optional[float]
    kill_screens: str
    catalyst_date: Optional[str]
    options_strategy: str  # long_calls, call_debit_spread, etc.

    # Risk management
    max_loss: float  # Limited to premium paid for long options

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


def preview_options_order(ticker: str, strike: float, expiration: str,
                          contracts: int, archetype: str,
                          right: str = "CALL",
                          options_strategy: str = "long_calls",
                          score: Optional[float] = None,
                          kill_screens: str = "PASS",
                          catalyst_date: Optional[str] = None) -> OptionsOrderPreview:
    """
    Create options order preview with all details.

    Args:
        ticker: Stock ticker (underlying)
        strike: Strike price
        expiration: Expiration date (YYYY-MM-DD)
        contracts: Number of contracts
        archetype: Trade archetype
        right: CALL or PUT
        options_strategy: Strategy type (long_calls, call_debit_spread, etc.)
        score: Total score from scoring filter
        kill_screens: Kill screen status
        catalyst_date: Catalyst date if applicable

    Returns:
        OptionsOrderPreview object
    """
    config = load_config()
    account_size = config["account"]["size"]

    # Fetch options data (Greeks, premium, IV)
    options_data = fetch_options_data(ticker, strike, expiration)

    if not options_data:
        raise ValueError(f"Could not fetch options data for {ticker} ${strike} {expiration}")

    premium_per_contract = options_data["mid_price"]

    # Calculate costs
    total_premium = premium_per_contract * contracts * 100  # 100 shares per contract
    notional_exposure = strike * contracts * 100  # Strike * contracts * multiplier

    # Portfolio sizing
    position_size_pct = (total_premium / account_size) * 100
    notional_pct = (notional_exposure / account_size) * 100

    # Calculate breakeven for long call
    if right == "CALL":
        breakeven = strike + premium_per_contract
    else:  # PUT
        breakeven = strike - premium_per_contract

    # Leverage ratio
    leverage_ratio = notional_exposure / total_premium if total_premium > 0 else 0

    # Calculate DTE
    from datetime import datetime
    exp_date = datetime.strptime(expiration, "%Y-%m-%d")
    dte = (exp_date - datetime.now()).days

    # Max loss for long options = premium paid
    max_loss = total_premium

    action = f"BUY_{right}"

    preview = OptionsOrderPreview(
        ticker=ticker.upper(),
        action=action,
        contracts=contracts,
        strike=strike,
        expiration=expiration,
        right=right.upper(),
        premium_per_contract=premium_per_contract,
        total_premium=total_premium,
        notional_exposure=notional_exposure,
        delta=options_data.get("delta"),
        theta=options_data.get("theta"),
        gamma=options_data.get("gamma"),
        vega=options_data.get("vega"),
        implied_volatility=options_data.get("implied_volatility"),
        breakeven_stock_price=breakeven,
        leverage_ratio=leverage_ratio,
        days_to_expiration=dte,
        position_size_pct=position_size_pct,
        notional_pct=notional_pct,
        account_size=account_size,
        archetype=archetype,
        score=score,
        kill_screens=kill_screens,
        catalyst_date=catalyst_date,
        options_strategy=options_strategy,
        max_loss=max_loss,
        timestamp=datetime.now().isoformat(),
        preview_id=f"{ticker}-OPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )

    return preview


def display_options_preview(preview: OptionsOrderPreview):
    """
    Display formatted options order preview to user.

    Args:
        preview: OptionsOrderPreview object
    """
    print()
    print("═" * 70)
    print(f"OPTIONS ORDER PREVIEW: {preview.action} {preview.ticker}")
    print("═" * 70)
    print(f"Ticker:           {preview.ticker}")
    print(f"Action:           {preview.action}")
    print(f"Contracts:        {preview.contracts}")
    print(f"Strike:           ${preview.strike:.2f}")
    print(f"Expiration:       {preview.expiration} ({preview.days_to_expiration} DTE)")
    print(f"Premium:          ${preview.premium_per_contract:.2f} per contract")
    print(f"Total Premium:    ${preview.total_premium:,.2f}")
    print(f"Notional Value:   ${preview.notional_exposure:,.2f} ({preview.contracts} contracts × {preview.strike} × 100)")
    print()
    print(f"Position Size:    {preview.position_size_pct:.2f}% of portfolio (premium)")
    print(f"Notional:         {preview.notional_pct:.2f}% of portfolio")
    print(f"Leverage:         {preview.leverage_ratio:.1f}x")
    print()
    print("Greeks:")
    if preview.delta:
        print(f"  - Delta:      {preview.delta:.3f}")
    if preview.theta:
        print(f"  - Theta:      ${preview.theta:.2f}/day per contract")
        theta_total = preview.theta * preview.contracts
        theta_pct = (abs(theta_total) / preview.total_premium) * 100 if preview.total_premium > 0 else 0
        print(f"                ${theta_total:.2f}/day total ({theta_pct:.2f}% of premium)")
    if preview.gamma:
        print(f"  - Gamma:      {preview.gamma:.4f}")
    if preview.vega:
        print(f"  - Vega:       {preview.vega:.3f}")
    if preview.implied_volatility:
        print(f"  - IV:         {preview.implied_volatility*100:.1f}%")
    print()
    print(f"Breakeven:        ${preview.breakeven_stock_price:.2f} stock price")
    print()
    print("Rationale:")
    print(f"  - Archetype:    {preview.archetype.upper()}")
    print(f"  - Strategy:     {preview.options_strategy}")
    if preview.score:
        print(f"  - Score:        {preview.score:.1f} (BUY)")
    print(f"  - Kill screens: {preview.kill_screens}")
    if preview.catalyst_date:
        print(f"  - Catalyst:     {preview.catalyst_date}")
    print()
    print(f"Max Loss:         ${preview.max_loss:,.2f} (premium paid)")
    print(f"Max Gain:         Unlimited (for long calls)")
    print()
    print("═" * 70)


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


def execute_options_order(preview: OptionsOrderPreview, dry_run: bool = False) -> Dict:
    """
    Execute options order via IBKR paper trading.

    Args:
        preview: OptionsOrderPreview object
        dry_run: If True, simulate without actual execution

    Returns:
        Dict with execution result
    """
    if dry_run:
        print("\n[DRY RUN MODE] Options order simulated, not executed")
        return {
            "status": "SIMULATED",
            "order_id": "DRY-RUN-OPT-12345",
            "ticker": preview.ticker,
            "action": preview.action,
            "contracts": preview.contracts,
            "strike": preview.strike,
            "expiration": preview.expiration,
            "premium": preview.premium_per_contract,
            "dry_run": True
        }

    # Execute via IBKR script (place_option command)
    try:
        script_path = Path(__file__).parent / "ibkr_paper.py"

        cmd = [
            sys.executable,
            str(script_path),
            "place_option",
            preview.ticker,
            "BUY",  # Always BUY for opening long options
            str(preview.contracts),
            "--strike", str(preview.strike),
            "--expiration", preview.expiration,
            "--right", preview.right,
            "--order-type", "LMT",
            "--limit", str(preview.premium_per_contract)
        ]

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
            "contracts": preview.contracts,
            "strike": preview.strike,
            "expiration": preview.expiration,
            "premium": preview.premium_per_contract,
            "ibkr_response": output
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "error": "Options order execution timed out",
            "ticker": preview.ticker
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "ticker": preview.ticker
        }


def log_order(preview: Union[OrderPreview, OptionsOrderPreview], execution_result: Dict):
    """
    Log order preview and execution to logs/orders/.

    Args:
        preview: OrderPreview or OptionsOrderPreview object
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

    # preview_option command
    parser_preview_opt = subparsers.add_parser("preview_option", help="Preview an options order")
    parser_preview_opt.add_argument("ticker", help="Stock ticker (underlying)")
    parser_preview_opt.add_argument("--strike", type=float, required=True, help="Strike price")
    parser_preview_opt.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")
    parser_preview_opt.add_argument("--contracts", type=int, required=True, help="Number of contracts")
    parser_preview_opt.add_argument("--right", choices=["CALL", "PUT"], default="CALL", help="Call or Put")
    parser_preview_opt.add_argument("--archetype", required=True, help="Trade archetype")
    parser_preview_opt.add_argument("--strategy", default="long_calls", help="Options strategy")
    parser_preview_opt.add_argument("--score", type=float, help="Score from scoring filter")
    parser_preview_opt.add_argument("--catalyst-date", help="Catalyst date")

    # execute_option command
    parser_execute_opt = subparsers.add_parser("execute_option", help="Execute options order with confirmation")
    parser_execute_opt.add_argument("ticker", help="Stock ticker (underlying)")
    parser_execute_opt.add_argument("--strike", type=float, required=True, help="Strike price")
    parser_execute_opt.add_argument("--expiration", required=True, help="Expiration date (YYYY-MM-DD)")
    parser_execute_opt.add_argument("--contracts", type=int, required=True, help="Number of contracts")
    parser_execute_opt.add_argument("--right", choices=["CALL", "PUT"], default="CALL", help="Call or Put")
    parser_execute_opt.add_argument("--archetype", required=True, help="Trade archetype")
    parser_execute_opt.add_argument("--strategy", default="long_calls", help="Options strategy")
    parser_execute_opt.add_argument("--score", type=float, help="Score from scoring filter")
    parser_execute_opt.add_argument("--catalyst-date", help="Catalyst date")
    parser_execute_opt.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    parser_execute_opt.add_argument("--yes", action="store_true", help="Skip confirmation")

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

    elif args.command == "preview_option":
        preview = preview_options_order(
            args.ticker,
            args.strike,
            args.expiration,
            args.contracts,
            args.archetype,
            right=args.right,
            options_strategy=args.strategy,
            score=args.score,
            catalyst_date=getattr(args, "catalyst_date", None)
        )

        display_options_preview(preview)

    elif args.command == "execute_option":
        preview = preview_options_order(
            args.ticker,
            args.strike,
            args.expiration,
            args.contracts,
            args.archetype,
            right=args.right,
            options_strategy=args.strategy,
            score=args.score,
            catalyst_date=getattr(args, "catalyst_date", None)
        )

        display_options_preview(preview)

        # Get confirmation
        if not getattr(args, "yes", False):
            confirmed = get_user_confirmation()
            if not confirmed:
                print("\nOptions order cancelled by user")
                sys.exit(0)

        # Execute
        print("\nExecuting options order...")
        result = execute_options_order(preview, dry_run=dry_run)

        # Log
        log_order(preview, result)

        # Display result
        if result["status"] in ["EXECUTED", "SIMULATED"]:
            print(f"\n✓ Options order {result['status'].lower()}: {result['ticker']} {preview.action} {preview.contracts} contracts")
            if "order_id" in result:
                print(f"  Order ID: {result['order_id']}")
            print(f"  Strike: ${preview.strike}, Expiration: {preview.expiration}")
        else:
            print(f"\n✗ Options order failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
