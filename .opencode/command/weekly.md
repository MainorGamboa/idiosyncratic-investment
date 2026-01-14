---
description: Execute the complete weekly review and maintenance workflow
agent: build
model: openai/gpt-5.2-codex
---

# Weekly Autonomous Review Cycle

## Full Cycle (Minimal User Intervention)

1. **Performance Review** (`review` skill)
   - Analyze all closed trades this week
   - Calculate win rate, avg return, P&L
   - Extract lessons learned from post-mortems
   - Identify patterns (what worked, what didn't)
   - Update pattern recognition for future trades
   - Flag any systematic issues (e.g., all PDUFA losses from single-arm studies)

2. **Deep Catalyst Scan** (`scan` skill with extended parameters)
   - Comprehensive scan of all sources (longer lookback + lookahead)
   - FDA PDUFA calendar (next 90 days)
   - SEC 13D filings (last 7 days + catch any missed)
   - Merger/spin-off announcements (all sources)
   - Legislative developments (bill calendars, ballot measures)
   - Insider cluster detection (Form 4 filings, 2-week windows)
   - Liquidation opportunities (SPAC trusts, CEF discounts, biotech cash screens)
   - **Goal**: Maintain 8-12 active catalyst events in pipeline
   - Archive completed/cancelled events to events_archive.json

3. **Watchlist Maintenance**
   - Review all files in universe/watchlist/
   - Check for stale items (>7 days old without position opened)
   - Re-score if material news or price changes (>10% move or major catalyst update)
   - Archive outdated events (catalyst passed, no longer relevant)
   - Clean up orphan watchlist files (event completed but file not removed)
   - Flag high-priority items for immediate action

4. **IBKR Full Reconciliation** (comprehensive sync)
   - Run: `python scripts/ibkr_paper.py positions --verbose`
   - Compare IBKR positions vs trades/active/*.json
   - **Discrepancy types:**
     - **Orphan IBKR positions**: Exists in IBKR, no trade file → Alert + optionally auto-create
     - **Orphan trade files**: Trade file exists, no IBKR position → Alert (position closed outside system?)
     - **Quantity mismatches**: Trade file shares ≠ IBKR shares → Alert + reconcile
     - **Price drift**: Entry price in file vs IBKR avg cost → Log (expected due to fills)
   - **Reconciliation actions:**
     - Display full reconciliation table
     - Ask: "Auto-create trade files for orphan positions? [y/N]"
     - If yes → Generate trade files from IBKR data (basic template, requires manual thesis entry)
     - Update trade files with correct quantities if mismatches
   - **Output**: Reconciliation report saved to logs/reconciliation/YYYY-MM-DD.log

5. **Framework Calibration Check**
   - Review kill screen effectiveness (how many PASSes hit screens vs scoring?)
   - Check if scoring thresholds need adjustment:
     - BUY threshold (8.25): Are we seeing expected 68% win rate?
     - CONDITIONAL threshold (6.5): Clear separation or too many edge cases?
   - Analyze archetype adjustments (Activist tiers, Legislative penalties)
   - Review exit protocol effectiveness (info parity weights, hard exits)
   - Flag any systematic issues:
     - Example: "All PDUFA losses this month from single-arm studies → Consider kill screen"
     - Example: "Merger arb spread compression underperforming → Adjust mispricing filter"
   - **Output**: Calibration notes (not auto-applied, requires user review)

6. **Weekly Summary**
   - **Performance Metrics:**
     - Week's P&L (total $, total %)
     - Win rate: {wins} / {total_closed} = {pct}%
     - Average hold time: {days}
     - Best trade: {TICKER} (+{pct}%)
     - Worst trade: {TICKER} (-{pct}%)
   - **Catalyst Pipeline:**
     - Active catalyst events: {N} (target: 8-12)
     - New catalysts added: {N}
     - Events archived: {N}
   - **Position Status:**
     - Active positions: {N} / {max}
     - Positions opened this week: {N}
     - Positions closed this week: {N}
   - **Regime Changes:**
     - VIX movement: {start} → {end} ({change})
     - Credit spread changes: {change} bps
     - Regime alerts triggered: {N}
   - **IBKR Reconciliation:**
     - Orphan positions found: {N} (created files: {N})
     - Quantity mismatches: {N} (reconciled: {N})
     - System integrity: {OK | NEEDS ATTENTION}
   - **Action Items for Next Week:**
     - High-priority events to analyze: {list}
     - Watchlist items to re-score: {list}
     - Framework calibration notes: {summary}
     - IBKR reconciliation follow-ups: {list}

## IBKR Reconciliation Detail

### What Gets Checked:
1. **Position existence**: IBKR ↔ trades/active/ both directions
2. **Quantities**: Shares/contracts match
3. **Entry prices**: Avg cost (IBKR) vs entry_price (trade file)
4. **Tickers**: Symbol consistency
5. **Account**: Correct IBKR account (paper vs live)

### Reconciliation Actions:
```
Found 2 discrepancies:

┌──────────┬─────────────────┬──────────────────┬────────────────────┐
│ Ticker   │ Issue           │ IBKR             │ Trade File         │
├──────────┼─────────────────┼──────────────────┼────────────────────┤
│ XYZ      │ Orphan (IBKR)   │ 50 shares @$100  │ (no file)          │
│ ABC      │ Qty Mismatch    │ 25 shares @$50   │ 30 shares @$50     │
└──────────┴─────────────────┴──────────────────┴────────────────────┘

Actions:
[1] Auto-create trade file for XYZ? [y/N]: y
    → Created TRD-20260110-XYZ-UNKNOWN.json (requires manual thesis entry)

[2] Update ABC trade file quantity to 25? [y/N]: y
    → Updated TRD-20260107-ABC-PDUFA.json: shares 30 → 25
    → Added note: "Reconciled from IBKR (partial exit outside system?)"
```

### Auto-Create Trade File Template:
When orphan IBKR position is found and user approves creation:

```json
{
  "trade_id": "TRD-20260110-XYZ-UNKNOWN",
  "ticker": "XYZ",
  "archetype": "unknown",
  "status": "active",
  "thesis": {
    "summary": "AUTO-GENERATED: Position found in IBKR without trade file. Requires manual entry.",
    "catalyst": "UNKNOWN - ENTER MANUALLY",
    "catalyst_date": null,
    "linked_event": null
  },
  "scoring": {
    "final_score": 0,
    "note": "Position opened outside idiosyncratic system. Score unknown."
  },
  "decision": {
    "action": "RECONCILED_FROM_IBKR",
    "date": "2026-01-10",
    "rationale": "Position exists in IBKR but no trade file found. Auto-created for tracking."
  },
  "position": {
    "entry_date": "UNKNOWN",
    "entry_price": 100.00,
    "shares": 50,
    "cost_basis": 5000.00,
    "size_percent": 0.20,
    "source": "ibkr_reconciliation"
  },
  "exit_plan": {
    "info_parity_weights": {"media": 1.0, "iv": 1.0, "price": 1.0},
    "thesis_break_triggers": ["ENTER MANUALLY"]
  },
  "monitoring": [
    {
      "date": "2026-01-10",
      "action": "RECONCILED",
      "notes": "Auto-created from IBKR position during weekly reconciliation"
    }
  ]
}
```

## Token-Efficient Design

Weekly deep-dive complements daily incremental work:
- **Daily**: Process 2-3 new events, monitor active positions, incremental scanning
- **Weekly**: Catch anything missed, deep analysis, learning, full reconciliation
- Weekly scans are broader (90 days forward vs 30 days daily)
- Full IBKR reconciliation (daily only flags discrepancies, weekly resolves)

## Relationship with bulk-process Command

- **bulk-process**: Pipeline only (scan → screen → analyze → score), no position management
- **weekly**: Full review + deep scan + reconciliation + calibration + learning
- **Use case**: Run weekly after bulk-process to catch any events bulk missed or for deeper catalyst discovery

Weekly is the "maintenance and learning" cycle, daily is the "execution" cycle, bulk-process is the "pipeline catchup" tool.

## Configuration

Weekly reconciliation controlled by CONFIG.json → automation:

```json
{
  "automation": {
    "ibkr_reconciliation": {
      "enabled": true,
      "frequency": "weekly",
      "auto_create_from_ibkr": false,
      "alert_threshold": "any"
    }
  }
}
```

- **ibkr_reconciliation.enabled**: Run reconciliation in weekly workflow
- **auto_create_from_ibkr**: If true, auto-creates files without asking (use with caution)
- **alert_threshold**: "any" (alert on any discrepancy) or "critical" (only orphans/qty mismatches)

## When to Run

- **Friday after market close**: Review week's performance before weekend
- **Sunday evening**: Prepare for upcoming week with fresh catalyst scan
- **Monthly**: Run on first Sunday of month for deeper calibration review
