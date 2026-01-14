---
description: Execute bulk screening and scoring of new events without opening positions.
agent: build
model: openai/gpt-5.2-codex
---
## Purpose

Process multiple new catalyst events through the full screening and scoring pipeline. Useful for weekly catchup, backlog processing, or post-scan batch analysis. Does NOT open, close, or monitor positions.

## Full Cycle (Automated with User Summary)

1. **Discover New Events** (`scan` skill)
   - Scan FDA PDUFA calendar
   - Scan SEC 13D filings (activists)
   - Find merger announcements
   - Activist 13Ds, Spin off, inside traders
   - Update universe/events.json
   - Identify high-priority events

2. **Filter Unscreened Events**
   - Load all events from universe/events.json
   - Filter to events WITHOUT linked_idea (no watchlist file created)
   - Filter to events with status = "tracking" (exclude completed/cancelled)
   - Sort by priority (high first), then by catalyst date (nearest first)
   - Apply max_events_per_day limit from CONFIG.json (default: 3)
   - Log: "Found {N} unscreened events, processing {limit} per batch limit"

3. **Process Pipeline (Batch)**
   - For each selected event:
     a. Run `screen {TICKER} {ARCHETYPE}` → If FAIL: Log to trades/passed/, skip to next
     b. Run `analyze {TICKER}` → Creates universe/watchlist/{TICKER}.md
     c. Run `score {TICKER}` → Updates watchlist with final score
   - Accumulate results in memory (don't trigger open skill)
   - **Error handling**: If screen→analyze→score fails for one event, log error and continue to next
   - Log each step outcome (PASS/FAIL, score, decision)

4. **Batch Summary**
   - Display all scored events in single summary table:
     - Ticker | Archetype | Score | Decision | Catalyst Date | Notes
   - Group by decision:
     - BUY (≥8.25): List all BUY decisions
     - CONDITIONAL (6.5-8.24): List all CONDITIONAL decisions
     - PASS (<6.5): List all PASS decisions
     - FAILED SCREENS: List all kill screen failures
   - Summary counts:
     - Total events processed: {N}
     - BUY decisions: {N}
     - CONDITIONAL decisions: {N}
     - PASS decisions: {N}
     - Failed screens: {N}

## Token Efficiency

- Limit batch size via CONFIG.json → automation.max_events_per_day (default: 3)
- Adjust based on average token usage per event (~2000-3000 tokens)
- Daily command can run this first, then handle position management separately

## When to Use

- Weekly: Process backlog of new events discovered by scan
- Post-vacation: Catch up on multiple new catalysts
- Bulk screening: Evaluate entire PDUFA calendar month
- Before daily: Pre-screen new events without mixing with position management

## What This Does NOT Do

- Does NOT open positions (no `open` skill)
- Does NOT close positions (no `close` skill)
- Does NOT monitor active trades (no `monitor` skill)
- Use `daily` command for full trading cycle including position management

## Example Output

```
═══════════════════════════════════════════════════════
BULK PROCESS SUMMARY: 3 events processed
═══════════════════════════════════════════════════════

BUY DECISIONS (2):
┌────────┬──────────┬───────┬──────────┬────────────────┬─────────────────────┐
│ Ticker │ Archtype │ Score │ Decision │ Catalyst Date  │ Notes               │
├────────┼──────────┼───────┼──────────┼────────────────┼─────────────────────┤
│ FBIO   │ PDUFA    │ 8.7   │ BUY      │ 2026-01-14     │ Rare disease, BTD   │
│ ATRA   │ PDUFA    │ 8.5   │ BUY      │ 2026-01-10     │ First-in-class      │
└────────┴──────────┴───────┴──────────┴────────────────┴─────────────────────┘

CONDITIONAL DECISIONS (0):
None

PASS DECISIONS (1):
┌────────┬──────────┬───────┬──────────┬────────────────┬─────────────────────┐
│ Ticker │ Archtype │ Score │ Decision │ Catalyst Date  │ Notes               │
├────────┼──────────┼───────┼──────────┼────────────────┼─────────────────────┤
│ AQST   │ PDUFA    │ 6.2   │ PASS     │ 2026-01-06     │ Weak catalyst       │
└────────┴──────────┴───────┴──────────┴────────────────┴─────────────────────┘

FAILED KILL SCREENS (0):
None

═══════════════════════════════════════════════════════
NEXT STEPS:
- 2 BUY decisions ready for position opening
- Run '/daily' to open positions with batch preview
- Or manually run 'open {TICKER}' for individual positions
═══════════════════════════════════════════════════════
```

## Configuration

Edit CONFIG.json → automation section:

```json
{
  "automation": {
    "max_events_per_day": 3,
    "batch_preview": true,
    "require_confirmation": true
  }
}
```

- `max_events_per_day`: Maximum events to process in single bulk-process run
- `batch_preview`: Show summary before any actions (always true for bulk-process)
- `require_confirmation`: Whether to ask user before processing (recommended: false for bulk-process, true for daily open)
