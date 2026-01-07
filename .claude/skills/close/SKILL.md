---
name: close
description: Close position and create post-mortem. Calculates returns, writes lessons learned, updates precedents index. Use when exit signal triggered, catalyst occurred, thesis invalidated, or stop loss hit.
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
```json
{
  "trade_id": "TRD-2025-001",
  "exit_price": 175.00,
  "exit_reason": "catalyst_complete|info_parity|cockroach|thesis_break|stop_loss|other"
}
```

**Parameters:**
- `trade_id` (required): Trade ID to close
- `exit_price` (required): Actual exit price
- `exit_reason` (required): Primary reason for exit

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

**Example preview:**
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

**Step 1b-2: Get User Confirmation**
Present the preview and wait for user confirmation (y/N).

**Step 1b-3: Execute Exit Order** (if confirmed)
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

**See TECHNICAL_SPEC.md §10 for complete order execution logic.**

**Order type:** Market order (immediate execution required)
- Rationale: Exit signals demand immediate action, slippage acceptable
- Time in force: IOC (Immediate or Cancel)

Market orders ensure execution when exit signal triggered (cockroach, thesis break, info parity).

### Step 2: Calculate Outcome
```javascript
gross_return_pct = (exit_price - entry_price) / entry_price
gross_return_usd = (exit_price - entry_price) * shares
hold_days = date_diff(exit_date, entry_date)

thesis_correct = (gross_return_pct > 0) // Simplified, refine based on thesis
```

### Step 3: Write Post-Mortem
Prompt for or analyze:

**What Worked:**
- Which filters/signals were accurate?
- Did precedents apply correctly?
- Was sizing appropriate?

**What Didn't Work:**
- Which assumptions were wrong?
- Did filters miss something?
- Was timing off?

**Lessons Learned:**
- New patterns discovered?
- Rule changes needed?
- Calibration adjustments?

**Tags to Add:**
- Pattern tags (e.g., `obvious_beneficiary`, `cockroach_exit`)
- Outcome tags (`positive_outcome`, `negative_outcome`, `neutral_outcome`)
- Archetype-specific tags

### Step 4: Update Trade JSON
Add outcome and post_mortem sections:

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

### Step 6: Update Precedents Index
Add tags to `precedents/index.json`:

```json
{
  "tags": {
    "breakthrough_adcom_combo": ["TRD-2025-001"],
    "pdufa_approval": ["TRD-2025-001"],
    "positive_outcome": ["TRD-2025-001"]
  }
}
```

### Step 7: Update Event (if linked)
If trade was linked to an event, update event status to "completed" in `universe/events.json`.

### Step 8: Write Log Entry

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
- Add specific, searchable tags to precedents index
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
- `search` — Find similar trades for comparison
- `review` — Aggregates closed trades in weekly review
