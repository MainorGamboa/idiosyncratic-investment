---
name: monitor
description: Update all active trades with current data and check exit signals. Evaluates info parity signals and hard exit triggers. Use daily as part of morning routine, or when significant market moves occur.
---

# Monitor Skill

## Purpose
Update all active trades with current data, check exit signals.

## When to Use
- Daily (morning routine)
- When significant market move occurs
- Before major catalyst dates

## Inputs
```json
{
  "trade_id": "TRD-2025-001"  // Optional, monitors all if omitted
}
```

## Process

### Step 1: Load Active Trades
Read all files in `trades/active/`

(Optional) Reconcile IBKR positions: `python scripts/ibkr_paper.py positions`

### Step 2: For Each Trade

#### A. Get Current Data (AUTOMATED)

**AUTOMATION: Use data_fetcher.py to fetch current market data**

For each active trade, run:
```bash
python scripts/data_fetcher.py fetch_price {TICKER}
python scripts/data_fetcher.py fetch_market_data {TICKER}
```

This automatically fetches:
- Current price (with source attribution)
- 200-day MA
- Options IV (if available)
- Recent news mentions (for media signal)
- Volume metrics

Display fetched data:
- Current price vs entry price (% change)
- Price vs 200-day MA
- IV current vs historical average
- Data quality and sources used

#### B. Check Info Parity Signals

| Signal | Threshold | Check |
|--------|-----------|-------|
| Media | 2+ articles | Search news |
| IV | >2x average | Compare current vs historical |
| Price | >50% to target | (current - entry) / (target - entry) |

#### C. Calculate Weighted Sum
```
weights = trade.exit_plan.info_parity_weights
weighted_sum = 
  (media_triggered * weights.media) +
  (iv_triggered * weights.iv) +
  (price_triggered * weights.price)
```

#### D. Check Hard Exit Triggers

**Cockroach Rule:**
- Any regulatory delay?
- Any financing wobble?
- Any board dissent?

**200-day MA:**
- Is price below 200-day MA?
- If yes → flag for defensive posture

**Thesis Break:**
- Check thesis_break_triggers from exit_plan
- Any triggered?

**Activist WARN Filing (v1.1):**
- **For activist archetype only**
- Check state WARN Act databases for company
- Use: `python scripts/warn_act_checker.py activist_exit {COMPANY_NAME}`
- If WARN filing contains "loss of contract" language → **IMMEDIATE EXIT**
- Rationale: Major contract loss invalidates activist operational fix thesis

#### E. Determine Action

| Condition | Action |
|-----------|--------|
| weighted_sum >= 3.0 | FULL EXIT |
| weighted_sum >= 2.0 | EXIT 50% |
| Cockroach observed | FULL EXIT |
| Thesis break | FULL EXIT |
| **Activist WARN filing (v1.1)** | **FULL EXIT** |
| Below 200-day MA | DEFENSIVE (tighten stop) |
| weighted_sum < 2.0 | HOLD (continue monitoring) |

### Step 3: Update Trade File

Add monitoring entry:

```json
{
  "date": "2025-01-15",
  "price": 128.00,
  "info_parity": {
    "media": 0,
    "iv": 0,
    "price": 0.19
  },
  "weighted_sum": 0.19,
  "ma_200": 115.00,
  "above_200_ma": true,
  "cockroaches": [],
  "action": "HOLD",
  "notes": "No mainstream coverage. IV normal. 19% to target."
}
```

### Step 4: Generate Alerts (if any triggered)

**See TECHNICAL_SPEC.md §14 for complete alerting specification.**

If exit signals detected, write to `alerts.json`:

```json
{
  "alerts": [
    {
      "id": "ALERT-{YYYYMMDDHHMMSS}",
      "timestamp": "2025-01-05T14:30:00Z",
      "priority": "immediate",
      "type": "exit_signal",
      "trade_id": "TRD-20250105-SRPT-PDUFA",
      "ticker": "SRPT",
      "message": "Info parity weighted sum = 2.1. Exit 50% recommended.",
      "details": {
        "current_price": 155.00,
        "entry_price": 125.50,
        "unrealized_gain_pct": 0.235,
        "weighted_sum": 2.1,
        "signals": {
          "media": true,
          "iv": true,
          "price": false
        }
      },
      "action_required": true,
      "acknowledged": false
    }
  ]
}
```

**Alert Priority Levels:**
- **immediate**: Exit signals (≥2.0), cockroach, stop loss, regime change
- **daily_digest**: Monitoring updates, P&L summaries
- **weekly_review**: Framework calibration, performance metrics

### Step 5: Write Log Entry

Append to `logs/monitor/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T09:30:00Z",
  "skill": "monitor",
  "outcome": "COMPLETE",
  "metrics": {
    "trades_monitored": 3,
    "alerts_generated": 1,
    "actions_required": 1
  },
  "data_sources": ["IBKR", "Yahoo Finance", "web search (news)"],
  "execution_time_ms": 3200,
  "notes": "1 exit signal detected (TRD-20250105-SRPT-PDUFA at weighted_sum 2.1)"
}
```

## Output

```json
{
  "trades_monitored": 3,
  "alerts": [],
  "actions_required": 0,
  "summary": "All positions stable. No exit signals triggered."
}
```

## Info Parity Weights by Archetype

| Archetype | Media | IV | Price |
|-----------|-------|-----|-------|
| merger_arb | 1.0 | 1.0 | 1.0 |
| spinoff | 0.5 | 1.0 | 1.5 |
| pdufa | 0.5 | 1.5 | 1.0 |
| activist | 1.0 | 0.5 | 1.0 |
| liquidation | 0.5 | 0.5 | 1.5 |
| insider | 1.0 | 1.0 | 1.0 |
| legislative | 1.0 | 1.0 | 1.0 |

## Exit Decision Tree

```
1. Check hard exits first:
   - Cockroach? → EXIT
   - Thesis break? → EXIT
   
2. Check weighted sum:
   - >= 3.0 → FULL EXIT
   - >= 2.0 → EXIT 50%
   
3. Check defensive:
   - Below 200-MA? → TIGHTEN STOP
   
4. Otherwise:
   - HOLD + update log
```

## Rules
- Run daily at minimum
- Check hard exits BEFORE info parity
- Always log monitoring entry, even if no action
- Note any cockroaches, even minor ones
