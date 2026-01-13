---
name: close
description: Close position and create post-mortem. Calculates returns, writes lessons learned. Use when exit signal triggered, catalyst occurred, thesis invalidated, or stop loss hit.
---

# Close Skill

## Purpose
Close position and create post-mortem. Moves trade to closed/, calculates outcome, documents lessons learned.

## When to Use
- Exit signal triggered (info parity, hard exit, etc.)
- Catalyst has occurred
- Thesis has changed or been invalidated
- Stop loss hit

## Inputs

**For Equity:**
```json
{
  "trade_id": "TRD-2025-001",
  "exit_price": 175.00,
  "exit_reason": "catalyst_complete|info_parity|cockroach|thesis_break|stop_loss|other"
}
```

**For Options:**
```json
{
  "trade_id": "TRD-2025-001",
  "exit_option_price": 8.50,
  "exit_reason": "catalyst_complete|info_parity|approaching_expiration|theta_decay|cockroach|thesis_break|other",
  "partial_close": false,
  "contracts_to_close": null
}
```

**Parameters:**
- `trade_id` (required): Trade ID to close
- `exit_price` (required for equity): Stock exit price
- `exit_option_price` (required for options): Option mid price at exit
- `exit_reason` (required): Primary reason for exit
- `partial_close` (optional for options): If true, close only portion of contracts
- `contracts_to_close` (optional for options): Number of contracts to close (for partial)

## Process

### Step 1: Load Active Trade
Read `trades/active/{TRADE_ID}.json`

### Step 1b: Exit Order Preview & Confirmation (AUTOMATED)

**AUTOMATION: Use order_manager.py for exit preview and execution**

**Step 1b-1: Generate Exit Preview**
```bash
python scripts/order_manager.py preview_exit {TICKER} \
  --trade-id {TRADE_ID} \
  --exit-reason {exit_reason}
```

This displays a formatted exit preview with:
- Current position details
- Entry vs exit price
- P&L ($ and %)
- Exit reason
- Days held

**Example Equity Preview:**
```
═══════════════════════════════════════════════════════
EXIT PREVIEW: SELL SRPT
═══════════════════════════════════════════════════════
Trade ID:         TRD-20260105-SRPT-PDUFA
Entry:            $125.50 × 30 shares = $3,765
Exit:             $175.00 × 30 shares = $5,250
P&L:              +$1,485 (+39.4%)
Days Held:        37
Exit Reason:      catalyst_complete

Annualized Return: 389%

═══════════════════════════════════════════════════════
Execute this exit? [y/N]: _
```

**Example Options Preview:**
```
═══════════════════════════════════════════════════════
OPTIONS EXIT PREVIEW: SELL TO CLOSE SRPT CALLS
═══════════════════════════════════════════════════════
Trade ID:          TRD-20260105-SRPT-PDUFA
Strategy:          Long Calls
Strike:            $130.00
Expiration:        2025-03-21
Contracts:         5

Entry:
  Premium Paid:    $3.50 × 5 × 100 = $1,750
  Underlying:      $125.50
  DTE at Entry:    70 days
  Entry Date:      2025-01-10

Exit:
  Premium Selling: $8.50 × 5 × 100 = $4,250
  Underlying Now:  $178.00
  DTE Remaining:   34 days
  Exit Date:       2025-02-15 (catalyst day)

P&L:
  Gross P&L:       +$2,500 (+142.9%)
  Theta Decay:     $350 (estimated)
  Net P&L:         +$2,150 (+122.9%)
  Days Held:       36

Performance vs Equity:
  Options Return:  +122.9%
  Stock Return:    +41.8% (if held stock)
  Leverage Factor: 2.9x

Exit Reason:       catalyst_complete
Catalyst:          FDA approval announced

═══════════════════════════════════════════════════════
Execute this exit? [y/N]: _
```

**Step 1b-2: Get User Confirmation**
Present the preview and wait for user confirmation (y/N).

**Step 1b-3: Execute Exit Order** (if confirmed)

**For Equity:**
```bash
python scripts/order_manager.py execute_exit {TICKER} \
  --trade-id {TRADE_ID} \
  --order-type MKT
```

This script:
1. Gets current market price
2. Places market order via IBKR
3. Confirms execution
4. Logs to `logs/orders/YYYY-MM-DD.log`

**Order type:** Market order (immediate execution required)
- Rationale: Exit signals demand immediate action, slippage acceptable
- Time in force: IOC (Immediate or Cancel)

**For Options:**
```bash
python scripts/order_manager.py execute_exit_options {TICKER} \
  --trade-id {TRADE_ID} \
  --order-type MKT \
  --action SELL_TO_CLOSE \
  --contracts {contracts}
```

This script:
1. Gets current options bid price
2. Places market order SELL TO CLOSE via IBKR
3. Confirms execution
4. Logs final Greeks and exit price to trade file
5. Logs to `logs/orders/YYYY-MM-DD.log`

**Order type:** Market order (immediate execution required)
- Rationale: Exit signals demand immediate action, options spreads wider than equity
- Time in force: IOC (Immediate or Cancel)
- Action: SELL TO CLOSE (closes long calls position)

**Important:** For partial closes (e.g., info parity = 1.5 → exit 50%):
- Calculate contracts to close: `floor(total_contracts * 0.50)`
- Update trade file with remaining contracts
- Keep trade in `active/` if partial close, move to `closed/` if full close

**See TECHNICAL_SPEC.md §10 for complete order execution logic.**

### Step 2: Calculate Outcome

**For Equity:**
```javascript
gross_return_pct = (exit_price - entry_price) / entry_price
gross_return_usd = (exit_price - entry_price) * shares
hold_days = date_diff(exit_date, entry_date)

thesis_correct = (gross_return_pct > 0) // Simplified, refine based on thesis
```

**For Options:**
```javascript
// P&L Calculation
premium_paid_per_contract = options_position.premium_per_contract
exit_premium_per_contract = exit_option_price
contracts_closed = contracts_to_close || options_position.contracts

gross_pnl_per_contract = (exit_premium_per_contract - premium_paid_per_contract) * 100
total_gross_pnl = gross_pnl_per_contract * contracts_closed / 100
total_premium_paid = premium_paid_per_contract * contracts_closed * 100

gross_return_pct = (exit_premium_per_contract - premium_paid_per_contract) / premium_paid_per_contract

// Account for theta decay
total_theta_decay = sum(all monitoring.greeks.theta) // Estimate from history
net_pnl = total_gross_pnl - abs(total_theta_decay)

// Calculate vs equity comparison
stock_entry = options_position.underlying_price_at_entry
stock_exit = current_underlying_price
stock_return_pct = (stock_exit - stock_entry) / stock_entry
leverage_factor = gross_return_pct / stock_return_pct

// Timing metrics
hold_days = date_diff(exit_date, entry_date)
dte_at_entry = options_position.dte_at_entry
dte_at_exit = calculate_dte(expiration, exit_date)
dte_used = dte_at_entry - dte_at_exit

thesis_correct = (gross_return_pct > 0)
```

### Step 3: Write Post-Mortem
Prompt for or analyze:

**What Worked:**
- Which filters/signals were accurate?
- Was sizing appropriate?
- **For Options:** Was expiration timing correct? Did leverage justify theta decay cost?

**What Didn't Work:**
- Which assumptions were wrong?
- Did filters miss something?
- Was timing off?
- **For Options:** Was strike selection optimal? Did theta decay too quickly? Should have used equity instead?

**Lessons Learned:**
- New patterns discovered?
- Rule changes needed?
- Calibration adjustments?
- **For Options:** Did options outperform equity? Was IV pricing fair? What was actual vs expected leverage?

**Tags to Add:**
- Pattern tags (e.g., `obvious_beneficiary`, `cockroach_exit`)
- Outcome tags (`positive_outcome`, `negative_outcome`, `neutral_outcome`)
- Archetype-specific tags
- **For Options:** `options_trade`, strategy tag (`long_calls`, `call_debit_spread`, `leaps`), `options_outperformed` or `equity_would_have_won`

### Step 4: Update Trade JSON
Add outcome and post_mortem sections:

**For Equity:**
```json
{
  "outcome": {
    "exit_date": "2025-02-16",
    "exit_price": 175.00,
    "exit_reason": "catalyst_complete",
    "gross_return_pct": 0.394,
    "gross_return_usd": 1485,
    "hold_days": 37,
    "thesis_correct": true,
    "annualized_return": 3.89
  },

  "post_mortem": {
    "what_worked": [
      "Catalyst clarity scoring was accurate",
      "Breakthrough + AdCom combination was high-conviction signal",
      "Exit timing was appropriate (day after PDUFA)"
    ],
    "what_didnt_work": [
      "Undersized position - could have taken full 1.5% given score 8.5"
    ],
    "lessons": [
      "Breakthrough + positive AdCom is high-conviction setup (base rate >95%)",
      "When score >8.5, bias toward max archetype size"
    ],
    "tags_added": [
      "breakthrough_adcom_combo",
      "pdufa_approval",
      "positive_outcome"
    ],
    "rule_changes": []
  }
}
```

**For Options:**
```json
{
  "options_outcome": {
    "exit_date": "2025-02-15",
    "exit_option_price": 8.50,
    "underlying_price_at_exit": 178.00,
    "exit_reason": "catalyst_complete",
    "contracts_closed": 5,
    "premium_paid_total": 1750,
    "premium_received_total": 4250,
    "gross_return_pct": 1.429,
    "gross_return_usd": 2500,
    "theta_decay_total": 350,
    "net_return_pct": 1.229,
    "net_return_usd": 2150,
    "hold_days": 36,
    "dte_at_entry": 70,
    "dte_at_exit": 34,
    "dte_used": 36,
    "thesis_correct": true,
    "annualized_return": 12.45,
    "vs_equity": {
      "stock_return_pct": 0.418,
      "options_return_pct": 1.229,
      "leverage_achieved": 2.94,
      "leverage_expected": 4.21,
      "options_outperformed": true,
      "advantage_pct": 0.811
    }
  },

  "post_mortem": {
    "what_worked": [
      "Options provided 2.9x leverage on PDUFA approval",
      "Expiration 35 days post-catalyst was appropriate timing buffer",
      "Exited day-of catalyst - captured full move, avoided post-announcement IV crush",
      "Strike selection (3.6% OTM) balanced leverage vs cost",
      "Theta decay was manageable (1.9%/day average)"
    ],
    "what_didnt_work": [
      "Actual leverage (2.9x) fell short of entry projection (4.2x) due to IV crush",
      "Could have used slightly closer strike (ATM) for higher delta"
    ],
    "lessons": [
      "PDUFA options work best when exited ON catalyst day (before IV crush)",
      "ATM calls may be preferable to OTM for PDUFA (higher delta, less IV sensitivity)",
      "Exit immediately on approval - don't wait for stock to run further",
      "Options clearly superior for binary catalysts with defined dates"
    ],
    "tags_added": [
      "options_trade",
      "long_calls",
      "pdufa_approval",
      "options_outperformed",
      "catalyst_day_exit",
      "positive_outcome"
    ],
    "options_analysis": {
      "strike_performance": "Good - ITM by $48 at exit",
      "expiration_timing": "Excellent - 34 DTE remaining, no urgency",
      "iv_behavior": "IV crushed post-approval (68% → 35%), exited before full crush",
      "theta_impact": "Low - only 36 days of decay vs 70 DTE purchased",
      "equity_comparison": "Options delivered 81% additional return vs equity approach"
    },
    "rule_changes": []
  }
}
```

### Step 5: Move to Closed with Outcome Classification

**See TECHNICAL_SPEC.md §15.2 for complete file organization.**

Determine outcome and move to appropriate directory:
- If `gross_return_pct > 0` → Move to `trades/closed/wins/{TRADE_ID}.md`
- If `gross_return_pct <= 0` → Move to `trades/closed/losses/{TRADE_ID}.md`

**Why .md not .json?**
Post-mortems are narrative documents (human-readable), so use Markdown.

Convert JSON to Markdown format:
- Start with JSON frontmatter (---  metadata ---)
- Body contains narrative post-mortem, what worked/didn't work, lessons

This organization enables better learning from outcomes (wins vs losses patterns).

### Step 6: Update Event (if linked)
If trade was linked to an event, update event status to "completed" in `universe/events.json`.

### Step 7: Write Log Entry

Append to `logs/close/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T17:00:00Z",
  "skill": "close",
  "trade_id": "TRD-20250105-SRPT-PDUFA",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "outcome": "WIN",
  "metrics": {
    "return_pct": 0.394,
    "return_usd": 1485,
    "hold_days": 37,
    "entry_price": 125.50,
    "exit_price": 175.00,
    "thesis_correct": true
  },
  "data_sources": ["IBKR exit order"],
  "execution_time_ms": 2100,
  "notes": "Catalyst occurred (PDUFA approval). Market order executed. Post-mortem complete."
}
```

## Output
```json
{
  "trade_id": "TRD-2025-001",
  "status": "closed",
  "outcome": {
    "return_pct": 0.394,
    "return_usd": 1485,
    "hold_days": 37,
    "thesis_correct": true
  },
  "post_mortem": {
    "lessons_count": 2,
    "tags_added": 3
  },
  "file": "trades/closed/TRD-2025-001.json",
  "precedents_updated": true
}
```

## Rules
- ALWAYS write post-mortem (even for small wins/losses)
- Document what DIDN'T work as much as what did
- Calculate annualized return for comparison across trades
- Note if rules need updating (but don't update automatically)
- Be honest about mistakes and missed signals

## Exit Reason Categories

| Reason | Description | Thesis Outcome |
|--------|-------------|----------------|
| `catalyst_complete` | Catalyst occurred as expected | Usually correct |
| `info_parity` | Edge dissipated (weighted sum ≥2) | Partial win |
| `cockroach` | First regulatory/board/financing issue | Usually correct to exit |
| `thesis_break` | Core assumption invalidated | Thesis wrong |
| `stop_loss` | Price hit stop loss | Depends |
| `regime_change` | Market regime shifted | Unrelated to thesis |
| `time_stop` | Held too long without catalyst | Timing wrong |

## Post-Mortem Quality Checklist
- [ ] Specific (not generic "good trade")
- [ ] Actionable (what to do differently)
- [ ] Tagged appropriately (searchable later)
- [ ] Honest about mistakes
- [ ] Includes numerical calibration (did score match outcome?)

## Related Skills
- `monitor` — Identifies when to close
- `review` — Aggregates closed trades in weekly review
