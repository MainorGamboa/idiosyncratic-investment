---
description: Execute the complete autonomous daily trading workflow
agent: build
model: openai/gpt-5.2-codex
---

## Full Cycle (Batch Preview + Confirmation)

1. **Update Regime** (`regime` skill)
   - Check VIX, credit spreads
   - Update CONFIG.json
   - Set market conditions
   - Alert if regime change (VIX spike, credit spread widening)

2. **Monitor Existing Positions** (`monitor` skill)
   - Check all active trades for exit signals
   - Calculate info parity weighted sums
   - Check hard exit triggers (cockroach, thesis break)
   - Generate alerts to alerts.json for positions with signals
   - **Auto-close on hard exits**: If cockroach or thesis break detected → Auto-execute `close` skill
   - **Alert on info parity**: If weighted_sum ≥ 2.0 → Add to alerts.json, proceed to Step 3

3. **Close Positions with Exit Signals** (`close` skill - triggered by monitor)
   - For each alert with exit signal (from Step 2):
     a. Load active trade JSON
     b. Display exit preview (P&L, days held, exit reason)
     c. Ask confirmation: "Execute exit for {TICKER}? [y/N]"
     d. If confirmed → Execute market order, create post-mortem, move to closed/
   - Summary: "{N} positions closed today"

4. **Discover New Events** (`scan` skill)
   - Scan FDA PDUFA calendar
   - Scan SEC 13D filings (activists)
   - Find merger announcements
   - Update universe/events.json
   - Identify high-priority events for processing

5. **Process New Events Pipeline** (Batch with Limits)
   - Filter events WITHOUT watchlist file (unscreened)
   - Apply max_events_per_day limit from CONFIG.json (default: 3)
   - For each event (up to limit):
     a. Run `screen` → If FAIL: Log to trades/passed/, skip
     b. Run `analyze` → Creates watchlist file
     c. Run `score` → Updates watchlist with score and decision
   - **Error handling**: If screen→analyze→score fails for one event, log error and continue to next
   - Accumulate BUY decisions (≥8.25) and CONDITIONAL decisions (6.5-8.24) for batch preview

6. **Batch Position Preview** (if any BUY decisions from Step 5)
   - Display all BUY decisions in single table:
     ```
     ═══════════════════════════════════════════════════════
     NEW POSITIONS - BATCH PREVIEW
     ═══════════════════════════════════════════════════════
     Found 2 BUY decisions from today's scan:

     ┌────────┬──────────┬───────┬────────┬────────────────┬─────────────┐
     │ Ticker │ Archtype │ Score │ Shares │ Entry Price    │ Position %  │
     ├────────┼──────────┼───────┼────────┼────────────────┼─────────────┤
     │ FBIO   │ PDUFA    │ 8.7   │ 28     │ $13.42         │ 1.5%        │
     │ ATRA   │ PDUFA    │ 8.5   │ 30     │ $12.50         │ 1.5%        │
     └────────┴──────────┴───────┴────────┴────────────────┴─────────────┘

     Total capital deployed: $751.60 (3.0% of portfolio)
     Current active positions: 3
     After opening: 5 active positions (within 10 limit ✓)

     ═══════════════════════════════════════════════════════
     Open all 2 positions? [y/N]: _
     ```
   - **Single confirmation** for batch (not per-position)
   - If confirmed → Loop through each BUY decision and run `open` skill
   - If declined → Log all to trades/conditional/ with note "user_declined_batch"
   - Respects max_positions limit from CONFIG.json (current: 10)
   - If batch would exceed limit → Show warning, ask to proceed with subset

7. **CONDITIONAL Decisions Handling**
   - Log all CONDITIONAL decisions (6.5-8.24) to trades/conditional/
   - Display summary: "{N} CONDITIONAL decisions logged for manual review"
   - User can manually run `open {TICKER}` after reviewing thesis

8. **Optional: IBKR Reconciliation** (if enabled in config)
   - Run: `python scripts/ibkr_paper.py positions`
   - Compare IBKR positions vs trades/active/*.json
   - Flag discrepancies:
     - Positions in IBKR but NOT in trades/active/ → Alert: "Position exists in IBKR without trade file"
     - Positions in trades/active/ but NOT in IBKR → Alert: "Trade file exists but position closed in IBKR"
   - Display reconciliation summary
   - **Future**: Auto-create missing trade files from IBKR positions (see CONFIG.json → automation.ibkr_reconciliation.auto_create_from_ibkr)

9. **Daily Summary**
   - Regime state (VIX, credit spreads, alerts)
   - Positions closed today: {N} (with P&L summary)
   - New events discovered: {N}
   - Events processed: {N} (of {max_events_per_day} limit)
   - Positions opened today: {N}
   - Active positions count: {current} / {max}
   - Alerts requiring attention: {N} (link to alerts.json)
   - IBKR reconciliation status (if enabled)

## Automation Controls

Configuration is in CONFIG.json → automation:

```json
{
  "automation": {
    "dry_run": false,
    "auto_approve_orders": false,
    "require_confirmation": true,
    "max_positions": 10,
    "max_events_per_day": 3,
    "batch_preview": true,
    "ibkr_reconciliation": {
      "enabled": false,
      "auto_create_from_ibkr": false
    },
    "batch_processing": {
      "enabled": true,
      "require_confirmation": true,
      "confirmation_style": "single"
    },
    "auto_close": {
      "cockroach_rule": true,
      "thesis_break": true,
      "info_parity_threshold": 2.0,
      "require_confirmation_for_info_parity": true
    }
  }
}
```

### Key Settings:
- **require_confirmation**: If true, shows batch preview and waits for [y/N] (default: true)
- **batch_preview**: If true, shows all BUY decisions in single table (default: true)
- **max_positions**: Maximum active positions (prevents overtrading)
- **max_events_per_day**: Limits pipeline processing to control token usage
- **auto_approve_orders**: If true, skips confirmation (USE WITH CAUTION in paper trading)
- **ibkr_reconciliation.enabled**: If true, runs IBKR sync in step 8
- **ibkr_reconciliation.auto_create_from_ibkr**: If true, creates trade files for orphan IBKR positions (future feature)
- **batch_processing.confirmation_style**: "single" (one approval for all) vs "individual" (per position)

## When Automation Triggers

**Auto-close (no confirmation needed):**
- Cockroach Rule triggered
- Thesis break triggered
- Stop loss hit

**Batch confirmation (single approval):**
- Multiple BUY decisions from pipeline → Show all, confirm once
- Close multiple positions with exit signals → Show all, confirm batch

**No confirmation (auto-log):**
- PASS decisions (<6.5) → Auto-log to trades/passed/
- CONDITIONAL decisions (6.5-8.24) → Auto-log to trades/conditional/
- Failed kill screens → Auto-log to trades/passed/

## Workflow Clarifications

### How Batch Preview Works:
1. Daily processes events through score skill
2. Accumulates all BUY decisions in memory
3. Displays single summary table with all positions
4. User confirms ONCE with [y/N]
5. If yes → Loop executes `open` for each ticker
6. If no → All decisions logged to trades/conditional/ as "user_declined_batch"

### How Close is Triggered:
1. Monitor skill detects exit signal (weighted_sum ≥ 2.0 or hard exit)
2. Monitor writes alert to alerts.json
3. Daily command reads alerts
4. For each alert → Run close skill (with confirmation per position)
5. Close skill shows exit preview → User confirms → Market order executed

### IBKR Reconciliation (Optional):
- **Purpose**: Ensure trades/active/ matches IBKR positions
- **When enabled**: Runs after monitor step (before new positions)
- **Detects**: Orphan positions in IBKR, orphan trade files, quantity mismatches
- **Actions**: Alerts user to discrepancies, optionally auto-creates missing files
- **Future**: Full two-way sync with auto_create_from_ibkr flag

## Token-Efficient Design

Daily cycle is optimized for token efficiency:
- **Incremental processing**: Max 3 events per day (configurable)
- **Batch confirmation**: Single approval for multiple opens (reduces back-and-forth)
- **Auto-logging**: PASS/CONDITIONAL decisions logged automatically
- **Targeted monitoring**: Only active positions checked
- **Lazy reconciliation**: IBKR sync optional (only when needed)

Use `weekly` command for deep-dive analysis and catchup.
Use `bulk-process` command for pipeline-only batch processing (scan → score without position management).
