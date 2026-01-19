---
name: open
description: Open new position from scored idea. Calculates position sizing, creates active trade JSON with monitoring plan. Use after score skill returns BUY decision or CONDITIONAL decision with confirmation.
---

# Open Skill

## Purpose
Open new position from scored idea. Creates active trade JSON with position sizing and monitoring plan.

## When to Use
- After `score` skill returns BUY decision (≥8.25)
- Or CONDITIONAL decision (6.5-8.24) with user confirmation
- Ready to enter position

## Inputs

**For Equity:**
```json
{
  "ticker": "SRPT",
  "entry_price": 125.50,
  "shares": 30,
  "archetype": "pdufa",
  "thesis": "PDUFA with positive AdCom...",
  "score": 8.5,
  "score_breakdown": {}
}
```

**For Options:**
```json
{
  "ticker": "SRPT",
  "use_options": true,
  "option_strategy": "long_calls",
  "strike": 130.00,
  "expiration": "2025-03-21",
  "option_premium": 3.50,
  "contracts": 5,
  "archetype": "pdufa",
  "thesis": "PDUFA with positive AdCom...",
  "score": 8.5,
  "score_breakdown": {},
  "catalyst_date": "2025-03-15"
}
```

**Parameters:**
- `ticker` (required): Stock symbol
- `use_options` (optional): If true, open options position instead of equity
- `entry_price` (required for equity): Stock entry price
- `shares` (optional for equity): Number of shares, OR will calculate from sizing rules
- `option_strategy` (required for options): "long_calls", "call_debit_spread", or "leaps_calls"
- `strike` (required for options): Strike price
- `expiration` (required for options): Expiration date (YYYY-MM-DD)
- `option_premium` (required for options): Premium per contract (total cost = premium * contracts * 100)
- `contracts` (optional for options): Number of contracts, OR will calculate from sizing rules
- `archetype` (required): One of 7 archetypes
- `thesis` (required): Brief thesis from score skill
- `score` (required): Final score from score skill
- `score_breakdown` (required): Full scoring breakdown
- `catalyst_date` (required for options): Catalyst date for expiration validation

## Process

### Step 1: Validate Score
- If score < 6.5 → ERROR "Score too low for entry"
- If 6.5 <= score < 8.25 → WARNING "Conditional score, confirm before proceeding"
- If score >= 8.25 → Proceed

### Step 1.5: Check Volume Timing (Insider/Spinoff Only)

**For Insider archetype:**
- If score ≥8.25 AND days_since_cluster < 90:
  - Fetch 20-day average volume from Stooq: `https://stooq.com/q/d/l/?s={ticker}.us&i=d`
  - Calculate current volume vs 20-day average
  - If current volume < 2x average: **WARN** "Consider waiting for volume confirmation (2x 20-day avg). Max wait: 90 days from cluster."
  - If current volume ≥ 2x average: Proceed with entry
- Reference: `schema/archetypes.json` → insider → entry_timing → volume_overlay

**For Spinoff archetype:**
- If days_since_spin in [30, 60]:
  - Fetch 20-day average volume from Stooq
  - Check if current volume <1.5x average AND price has stabilized
  - If volume still elevated: **WARN** "Volume suggests continued forced selling. Consider waiting."
  - If volume normalized: Proceed with entry
- Reference: `schema/archetypes.json` → spinoff → entry_timing → volume_signal

**For all other archetypes:** Skip volume check (not applicable)

### Step 1.6: Options-Specific Validation (If use_options=true)

**Check Archetype Support:**
- Reference: `schema/options_strategies.json` → archetype_strategies → {archetype} → enabled
- If archetype doesn't support options (spinoff, liquidation, legislative) → ERROR "Options not supported for this archetype"
- If archetype supports but with restrictions (e.g., Activist Tier-3) → ERROR "Options only for Tier-1/Tier-2 activists"

**Validate Expiration:**
- Calculate DTE: `days_between(expiration, today)`
- Check minimum: DTE >= 21 days (from CONFIG.json → options_risk → expiration_rules → min_dte)
- Check catalyst alignment: expiration > catalyst_date + buffer_days
- Example: PDUFA 2025-03-15, buffer 7 days → expiration must be >= 2025-03-22

**Validate Strategy:**
- Check strategy in CONFIG.json → options_risk → allowed_strategies
- Allowed: "long_call", "call_debit_spread", "leaps_calls"
- If strategy not in list → ERROR "Strategy not allowed"

**Fetch Current Options Data:**
- Query IBKR/Yahoo for current bid/ask on specified strike and expiration
- Verify option_premium is within 10% of current mid price
- If premium differs >10% → WARN "Specified premium differs from current market, using current mid: $X.XX"
- Check open interest and bid-ask spread (should already be validated by analyze skill, but double-check)

**Check Regime Adjustments:**
- If VIX 20-30: Reduce calculated position by 25%
- If VIX >30: Reduce calculated position by 50%
- If HY OAS widened and archetype=merger_arb → ERROR "Merger arb options paused due to credit spread widening"

### Step 2: Calculate Position Size
Reference: `schema/archetypes.json`, `CONFIG.json`, and `schema/options_sizing.json`

**FOR EQUITY:**

```
account_size = CONFIG.json["account"]["size"]
archetype_max = archetypes[archetype]["position"]["max_size"]
kelly_fraction = archetypes[archetype]["position"]["kelly"]

max_position_size = account_size * archetype_max
kellner_loss_limit = account_size * 0.02  # Max 2% loss per trade

position_value = min(max_position_size, calculated_from_kelly)
```

**Kelly Fractions by Archetype:**
- Negative skew (Merger, PDUFA, Activist): 25% of Kelly
- Positive skew (Spin-off, Liquidation): 50% of Kelly

**v1.1 Position Sizing Adjustments:**

**For Spin-off archetype:**
- Check for WARN Act filing at SpinCo
- Use: `python scripts/warn_act_checker.py spinoff_sizing {SPINCO_NAME} {PARENT_NAME}`
- **If WARN filing detected → Reduce position size by 50%**
- Rationale: WARN signals operational distress at SpinCo, warrants risk reduction
- Reference: `schema/archetypes.json` → spinoff → operational_risk_signals

Example calculation with WARN adjustment:
```
base_position_value = min(max_position_size, calculated_from_kelly)
if spinoff_has_warn:
    adjusted_position_value = base_position_value * 0.5
else:
    adjusted_position_value = base_position_value
```

**FOR OPTIONS:**

Reference: `schema/options_sizing.json` → archetype_sizing → {archetype}

```
account_size = CONFIG.json["account"]["size"]
max_premium_at_risk = options_sizing[archetype]["max_premium_at_risk"]

# Calculate max premium dollars
max_premium_dollars = account_size * max_premium_at_risk

# Calculate contracts from premium
contract_cost = option_premium * 100
contracts = floor(max_premium_dollars / contract_cost)

# Apply regime adjustments
if VIX 20-30:
    contracts = floor(contracts * 0.75)  # Reduce 25%
elif VIX > 30:
    contracts = floor(contracts * 0.50)  # Reduce 50%

# Apply archetype-specific adjustments
if archetype == "pdufa" and IV_percentile > 75:
    contracts = floor(contracts * 0.75)  # Expensive options

# Verify portfolio limits
total_premium_all_positions = sum(all active options premiums)
if (total_premium_all_positions + contracts * contract_cost) > account_size * 0.10:
    contracts = floor((account_size * 0.10 - total_premium_all_positions) / contract_cost)
    WARN "Reduced position to stay under 10% total options premium limit"

# Calculate notional exposure and verify
notional = contracts * 100 * current_stock_price * delta
if notional > account_size * max_notional_exposure:
    contracts = floor(account_size * max_notional_exposure / (100 * current_stock_price * delta))
    WARN "Reduced position to stay under notional exposure limit"

# Final contract count (always round down)
final_contracts = max(1, contracts)
total_premium_paid = final_contracts * contract_cost
```

**Options Sizing Quick Reference:**

| Archetype | Max Premium % | Max Notional % | Example ($25k account) |
|-----------|---------------|----------------|------------------------|
| PDUFA | 1.5% | 5% | $375 premium, $1,250 notional |
| Activist T1 | 4% | 10% | $1,000 premium, $2,500 notional |
| Activist T2 | 3% | 8% | $750 premium, $2,000 notional |
| Merger Arb | 2% | 6% | $500 premium, $1,500 notional |
| Insider | 3% | 8% | $750 premium, $2,000 notional |

**Always Enforce:**
- Total portfolio options premium < 10%
- Total portfolio notional exposure < 30%
- Max 5 simultaneous options positions
- All options use 25% Kelly (more conservative than equity)

### Step 3: Generate Trade ID

**See TECHNICAL_SPEC.md §15.1 for complete trade ID specification.**

Format: `TRD-YYYYMMDD-TICKER-ARCHETYPE`

Examples:
- `TRD-20250105-SRPT-PDUFA`
- `TRD-20250110-ABBV-ACTIVIST`
- `TRD-20250115-TRUP-SPINOFF`

Benefits:
- Readable without opening file
- Sortable by date
- Grep-friendly
- Self-documenting (ticker and archetype visible)

### Step 4: Create Active Trade File
Create `trades/active/{TRADE_ID}.json`:

**FOR EQUITY:**
```json
{
  "trade_id": "TRD-2025-001",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "status": "active",
  "instrument_type": "equity",

  "thesis": {
    "summary": "PDUFA with positive AdCom, breakthrough therapy",
    "catalyst": "FDA decision",
    "catalyst_date": "2025-02-15",
    "linked_event": "EVT-2025-001"
  },

  "scoring": {
    "catalyst": 2.0,
    "mispricing": 1.5,
    "noise_survival": 1.5,
    "downside_floor": 1.0,
    "risk_reward": 1.5,
    "info_half_life": 1.0,
    "base_score": 8.5,
    "adjustments": [],
    "final_score": 8.5
  },

  "decision": {
    "action": "BUY",
    "date": "2025-01-10",
    "rationale": "Score 8.5 above threshold 8.25. Strong catalyst clarity."
  },

  "position": {
    "entry_date": "2025-01-10",
    "entry_price": 125.50,
    "shares": 30,
    "cost_basis": 3765,
    "size_percent": 0.015,
    "stop_price": 95.00,
    "target_price": 180.00
  },

  "exit_plan": {
    "info_parity_weights": {
      "media": 0.5,
      "iv": 1.5,
      "price": 1.0
    },
    "thesis_break_triggers": [
      "FDA delay announcement",
      "Manufacturing hold",
      "Negative efficacy data"
    ]
  },

  "monitoring": [],
}
```

**FOR OPTIONS:**
```json
{
  "trade_id": "TRD-2025-001",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "status": "active",
  "instrument_type": "options",

  "thesis": {
    "summary": "PDUFA with positive AdCom, breakthrough therapy - using options for leverage",
    "catalyst": "FDA decision",
    "catalyst_date": "2025-02-15",
    "linked_event": "EVT-2025-001"
  },

  "scoring": {
    "catalyst": 2.0,
    "mispricing": 1.5,
    "noise_survival": 1.5,
    "downside_floor": 1.0,
    "risk_reward": 1.5,
    "info_half_life": 1.0,
    "base_score": 8.5,
    "adjustments": [],
    "final_score": 8.5
  },

  "decision": {
    "action": "BUY_OPTIONS",
    "date": "2025-01-10",
    "rationale": "Score 8.5 above threshold. Options preferred due to binary catalyst with defined date. Leverage 4.2x vs equity."
  },

  "options_position": {
    "entry_date": "2025-01-10",
    "strategy": "long_calls",
    "underlying_price_at_entry": 125.50,
    "strike": 130.00,
    "expiration": "2025-03-21",
    "dte_at_entry": 70,
    "contracts": 5,
    "premium_per_contract": 3.50,
    "total_premium_paid": 1750,
    "premium_percent_portfolio": 0.015,
    "notional_exposure": 7375,
    "notional_percent_portfolio": 0.0295,
    "delta_at_entry": 0.55,
    "theta_per_day": -2.50,
    "implied_volatility": 0.68,
    "iv_percentile": 62,
    "breakeven_stock_price": 133.50,
    "breakeven_move_pct": 0.0638,
    "effective_leverage": 4.21
  },

  "options_exit_plan": {
    "catalyst_occurs_before_expiration": {
      "action": "Close position on catalyst day or info parity signal",
      "note": "Don't hold through expiration if catalyst occurred"
    },
    "approaching_expiration": {
      "dte_threshold": 14,
      "action": "Close or roll to next expiration",
      "note": "If theta decay > 5% premium/day, close early"
    },
    "info_parity_weights": {
      "media": 0.5,
      "iv": 1.5,
      "price": 1.0,
      "note": "PDUFA-specific weights, adjusted for options"
    },
    "info_parity_thresholds": {
      "exit_50_percent": 1.5,
      "full_exit": 2.5,
      "note": "Lower than equity (2.0/3.0) due to theta decay"
    },
    "thesis_break_triggers": [
      "FDA delay announcement",
      "Manufacturing hold",
      "Negative efficacy data",
      "Expiration < 14 DTE with catalyst not occurred"
    ],
    "theta_decay_alert": {
      "threshold_pct_per_day": 0.05,
      "action": "Review position if daily decay > 5% of remaining premium"
    }
  },

  "monitoring": [],
  "options_greeks_history": [],
}
```

### Step 5: Order Preview & Confirmation (AUTOMATED)

**AUTOMATION: Use order_manager.py for preview and execution**

**Step 5a: Generate Order Preview**

**For Equity:**
```bash
python scripts/order_manager.py preview {TICKER} BUY {shares} \
  --archetype {archetype} \
  --score {score} \
  --entry-price {entry_price} \
  --stop-price {stop_price}
```

**For Options:**
```bash
python scripts/order_manager.py preview {TICKER} BUY_OPTIONS {contracts} \
  --archetype {archetype} \
  --score {score} \
  --strike {strike} \
  --expiration {expiration} \
  --option-premium {premium} \
  --catalyst-date {catalyst_date}
```

This displays a formatted order preview with:
- Order details (ticker, action, contracts/shares, price)
- Position sizing (% of portfolio, within archetype limits)
- Risk metrics (max loss, Greeks for options)
- Rationale (archetype, score, kill screens, timing)

**Example Equity Preview:**
```
═══════════════════════════════════════════════════════
ORDER PREVIEW: BUY SRPT
═══════════════════════════════════════════════════════
Ticker:           SRPT
Action:           BUY
Shares:           30
Limit Price:      $125.50 (bid/ask midpoint)
Total Cost:       $3,765.00
Position Size:    1.51% of portfolio ($25,000)

Rationale:
- Archetype: PDUFA
- Score: 8.7 (BUY)
- Kill screens: PASS (M-Score -1.23, Z-Score 2.1)
- PDUFA date: 2026-02-15 (41 days)
- Entry timing: Optimal (days -45 to -30)

Max Loss (Kellner): $500 (2% of portfolio)
Stop Price:         $95.00 (-24% from entry)

═══════════════════════════════════════════════════════
Execute this order? [y/N]: _
```

**Example Options Preview:**
```
═══════════════════════════════════════════════════════
OPTIONS ORDER PREVIEW: BUY CALLS ON SRPT
═══════════════════════════════════════════════════════
Ticker:              SRPT
Underlying Price:    $125.50
Action:              BUY TO OPEN
Strategy:            Long Calls
Contracts:           5
Strike:              $130.00 (3.6% OTM)
Expiration:          2025-03-21 (70 DTE)
Premium/Contract:    $3.50
Total Premium:       $1,750.00
Notional Exposure:   $6,500 (5 contracts × 100 shares × $130)
Delta-Adj Notional:  $3,458 (delta 0.53)

Position Sizing:
- Premium: 1.5% of portfolio ($25,000) ✓
- Notional: 2.9% of portfolio ✓
- Archetype Max: 1.5% (PDUFA) ✓
- Total Options Premium: 1.5% of 10% limit ✓

Greeks at Entry:
- Delta: 0.53 (53% probability ITM)
- Theta: -$2.50/day ($125/month decay)
- IV: 68% (62nd percentile)
- Vega: 0.15

Breakeven Analysis:
- Breakeven Stock Price: $133.50
- Required Move: +6.4% from current
- Expected Move (thesis): +43% on approval
- Risk/Reward: Risk $1,750 to make $6,000+ (3.4:1)

Rationale:
- Archetype: PDUFA
- Score: 8.7 (BUY)
- Catalyst: FDA decision 2025-02-15 (36 days)
- Expiration: 35 days AFTER catalyst ✓
- Options kill screens: PASS (OI 250, spread 8%, liquidity ✓)
- Leverage: 3.7x vs equity approach

Risk Metrics:
- Max Loss: $1,750 (premium only, 1.5% portfolio)
- Daily Theta Decay: $2.50 (0.01% portfolio/day)
- Approaching Exp Alert: DTE < 14 days
- Info Parity Threshold: 1.5 (vs 2.0 for equity)

═══════════════════════════════════════════════════════
Execute this order? [y/N]: _
```

**Step 5b: Get User Confirmation**
Present the preview and wait for user confirmation (y/N).

**Step 5c: Execute Order** (if confirmed)

**For Equity:**
```bash
python scripts/order_manager.py execute {TICKER} BUY {shares} \
  --order-type LMT \
  --limit {midpoint_price}
```

This script:
1. Gets current bid/ask quotes
2. Calculates midpoint: `(bid + ask) / 2`
3. Places limit order via IBKR
4. Tracks order status
5. Logs execution to `logs/orders/YYYY-MM-DD.log`

**Order type:** Limit order at bid/ask midpoint
- Rationale: Better price, acceptable no-fill risk for non-urgent entries
- Time in force: DAY

**Retry logic:**
- If not filled after 30 minutes:
  - Check if price moved >5% from limit → Cancel, mark "missed entry"
  - Otherwise → Adjust limit to new midpoint, retry

**For Options:**
```bash
python scripts/order_manager.py execute {TICKER} BUY_OPTIONS {contracts} \
  --order-type LMT \
  --strike {strike} \
  --expiration {expiration} \
  --right CALL \
  --limit {option_midpoint_price}
```

This script:
1. Gets current options bid/ask for specified strike and expiration
2. Calculates midpoint: `(bid + ask) / 2`
3. Places limit order via IBKR for options contract
4. Tracks order status
5. Logs execution to `logs/orders/YYYY-MM-DD.log`

**Order type:** Limit order at bid/ask midpoint
- Rationale: Options spreads can be wide, avoid paying ask
- Time in force: DAY
- Right: CALL (for long calls strategy)

**Retry logic:**
- If not filled after 15 minutes (faster than equity due to wider spreads):
  - Check if midpoint moved >15% → Adjust to new midpoint, retry
  - If underlying stock moved >5% → Re-evaluate position, may cancel
  - Maximum 3 retries within same trading day

**Options-Specific Execution Notes:**
- Always use limit orders (NEVER market orders for options - spreads too wide)
- Verify Greeks after fill match expectations (delta, theta within 10%)
- Log entry Greeks to options_greeks_history array in trade file
- Calculate realized premium after fill (may differ slightly from preview)

**See TECHNICAL_SPEC.md §10 for complete order execution logic.**

### Step 6: Link to Event (if applicable)
If there's a linked event in `universe/events.json`, update the event's `linked_idea` field.

### Step 7: Write Log Entry

Append to `logs/open/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T16:30:00Z",
  "skill": "open",
  "trade_id": "TRD-20250105-SRPT-PDUFA",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "outcome": "SUCCESS",
  "metrics": {
    "entry_price": 125.50,
    "shares": 30,
    "position_value": 3765,
    "position_pct": 0.015,
    "archetype_max_pct": 0.015,
    "score": 8.5,
    "binding_constraint": "archetype_cap"
  },
  "data_sources": ["IBKR quotes", "CONFIG.json"],
  "execution_time_ms": 1850,
  "notes": "BUY decision executed. Limit order filled at midpoint."
}
```

## Output
```json
{
  "trade_id": "TRD-2025-001",
  "file": "trades/active/TRD-2025-001.json",
  "ticker": "SRPT",
  "entry_price": 125.50,
  "shares": 30,
  "position_size_pct": 0.015,
  "archetype_max_pct": 0.015,
  "within_limits": true,
  "next_step": "Run 'monitor' skill daily to track position"
}
```

## Rules
- NEVER exceed archetype max_size
- ALWAYS enforce Kellner rule (max 2% portfolio loss)
- Calculate stop_price to limit loss to 2% of portfolio
- Set target_price based on thesis upside
- Include info_parity_weights specific to archetype (from schema/exits.json)
- Create monitoring array (empty initially, populated by monitor skill)
- Link to event_id if catalyst is in events.json

## Position Sizing Quick Reference

| Archetype | Max Size | Kelly | Stop Loss |
|-----------|----------|-------|-----------|
| Merger Arb | 3% | 25% | Per deal spread |
| PDUFA | 1.5% | 25% | 2% portfolio max |
| Activist | 6% | 25% | 2% portfolio max |
| Spin-off | 8% | 50% | 2% portfolio max |
| Liquidation | 10% | 50% | NAV discount |
| Insider | 5% | 25% | 2% portfolio max |
| Legislative | 2% | 25% | 2% portfolio max |

## Related Skills
- `score` — Run before open (determines if position warranted)
- `monitor` — Run daily after opening position
- `close` — Close position when exit criteria met
