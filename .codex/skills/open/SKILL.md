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

**Parameters:**
- `ticker` (required): Stock symbol
- `entry_price` (required): Actual entry price
- `shares` (optional): Number of shares, OR will calculate from sizing rules
- `archetype` (required): One of 7 archetypes
- `thesis` (required): Brief thesis from score skill
- `score` (required): Final score from score skill
- `score_breakdown` (required): Full scoring breakdown

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

### Step 2: Calculate Position Size
Reference: `schema/archetypes.json` and `CONFIG.json`

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

```json
{
  "trade_id": "TRD-2025-001",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "status": "active",

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

  "precedents": [],
  "tags": ["{archetype}", "active"]
}
```

### Step 5: Place Entry Order

**See TECHNICAL_SPEC.md §10 for complete order execution logic.**

**Order type:** Limit order at bid/ask midpoint
- Rationale: Better price, acceptable no-fill risk for non-urgent entries
- Time in force: DAY

**Process:**
1. Get current bid/ask quotes for {ticker}
2. Calculate midpoint: `(bid + ask) / 2`
3. Place limit order at midpoint
4. If not filled after 30 minutes:
   - Check if price moved >5% from limit → Cancel, mark "missed entry"
   - Otherwise → Adjust limit to new midpoint, retry

**Execution** (if using IBKR paper):
```bash
python scripts/ibkr_paper.py place {ticker} BUY {shares} --order-type LMT --limit {midpoint_price}
```

Track order status and log entry price once filled.

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
