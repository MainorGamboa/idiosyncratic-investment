# Workflow Automation System

## Overview

The workflow automation system uses Claude Code slash commands to chain skills together, eliminating manual step-by-step execution. Commands are stored in `.claude/commands/` and can be invoked with `/command-name`.

## Command Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SLASH COMMANDS                            │
│                    (.claude/commands/*.md)                       │
└────────────┬─────────────────────────────────────┬──────────────┘
             │                                     │
             ▼                                     ▼
    ┌─────────────────┐                  ┌─────────────────┐
    │  SKILLS LAYER   │                  │   DATA LAYER    │
    │ (.codex/skills) │◄─────────────────┤ (schema/*.json) │
    └────────┬────────┘                  └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  FILE OUTPUTS   │
    │ (trades/, logs/)│
    └─────────────────┘
```

## Automated Workflows

### 1. Daily Morning Routine (`/daily`)

```
START
  │
  ├─► regime skill ────► Update CONFIG.json (VIX, HY OAS)
  │
  ├─► monitor skill ───► Check active trades for exit signals
  │
  ├─► Read alerts.json ─► Display active alerts
  │
  └─► Summary ─────────► Regime state + Action items
```

**Output**: Updated CONFIG.json, alerts, monitoring logs

---

### 2. New Idea Analysis (`/analyze-idea TICKER`)

```
START: TICKER provided
  │
  ├─► screen skill ────► Kill screens (M-Score, Z-Score, etc.)
  │                       │
  │                       ├─ FAIL ──► Log to trades/passed/
  │                       │            EXIT WORKFLOW
  │                       │
  │                       └─ PASS ──► Continue
  │
  ├─► analyze skill ───► Full analysis + watchlist creation
  │                       (universe/watchlist/TICKER.md)
  │
  ├─► score skill ─────► 6-filter scoring
  │                       │
  │                       ├─ <6.5 (PASS) ──► Log to trades/passed/
  │                       │
  │                       ├─ 6.5-8.24 (CONDITIONAL) ──► Explain confirmation needed
  │                       │
  │                       └─ ≥8.25 (BUY) ──► Prompt user: "Open position?"
  │                                           │
  │                                           └─ YES ──► open skill
  │                                                      (creates trades/active/*.json)
  │
  └─► Display final score and recommendation
```

**Output**: Watchlist file, scored analysis, optional active trade

---

### 3. Quick Status Check (`/quick-check`)

```
START
  │
  ├─► Read CONFIG.json ─► Display regime (VIX, credit)
  │
  ├─► monitor skill ───► Check active trades
  │
  ├─► Read alerts.json ─► Show active alerts
  │
  └─► Calculate P&L ───► Quick summary
```

**Output**: Status summary (no file changes)

---

### 4. Weekly Review (`/weekly-review`)

```
START
  │
  ├─► review skill ────► Generate weekly report
  │                       (performance, closed trades, lessons)
  │
  ├─► scan skill ──────► Update catalyst calendar
  │                       (FDA PDUFA, SEC 13D, earnings)
  │
  ├─► Check watchlist ─► Flag stale items (>7 days old)
  │
  └─► Display summary ─► Performance metrics + action items
```

**Output**: Review report, updated events.json, stale watchlist alerts

---

### 5. Close Position (`/close-trade TRADE_ID`)

```
START: TRADE_ID provided
  │
  └─► close skill ─────► Close position workflow
                          │
                          ├─► Calculate P&L
                          │
                          ├─► Create post-mortem
                          │   (trades/closed/wins/ or losses/)
                          │
                          ├─► Update precedents/index.json
                          │
                          └─► Archive from trades/active/

```

**Output**: Post-mortem file, updated precedents, archived trade

---

## Typical Usage Patterns

### Daily Pattern

```bash
# Morning (before market open)
/daily

# During market hours (new idea discovered)
/analyze-idea SRPT

# Afternoon (exit signal triggered)
/close-trade TRD-20250105-SRPT-PDUFA

# Intraday check (after VIX spike)
/quick-check
```

### Weekly Pattern

```bash
# Friday after market close OR Sunday evening
/weekly-review
```

## Manual vs Automated

| Task | Manual Method | Automated Method |
|------|---------------|------------------|
| Morning routine | `/skill regime` then `/skill monitor` | `/daily` |
| Analyze new idea | `/skill screen TICKER` → `/skill analyze TICKER` → `/skill score TICKER` | `/analyze-idea TICKER` |
| Check status | Read CONFIG.json, check alerts.json, run monitor | `/quick-check` |
| Close position | `/skill close TRADE_ID` | `/close-trade TRADE_ID` |
| Weekly review | `/skill review` then `/skill scan` | `/weekly-review` |

## Benefits

1. **Fewer steps**: One command instead of 3-5 skill invocations
2. **Fail-fast**: Workflows stop immediately if kill screens fail
3. **User prompts**: Commands ask for confirmation before high-stakes actions
4. **Consistent**: Same workflow every time, no missed steps
5. **Traceable**: All decisions still logged to appropriate files

## Extension Points

Add new commands by creating `.claude/commands/your-command.md`:

```markdown
# Your Command

Describe what the command does.

1. Step 1: Run skill X
2. Step 2: Run skill Y
3. Step 3: Display result

Use when: [describe use case]
```

Claude Code will automatically discover and execute the workflow.

## Integration with Existing System

- **Skills remain unchanged**: Commands orchestrate existing skills
- **Schemas still authoritative**: Commands don't bypass framework rules
- **Logging still happens**: Each skill logs to its own log directory
- **User control**: Commands prompt before irreversible actions (open/close positions)

## Next Steps

1. Test `/daily` command tomorrow morning
2. Use `/analyze-idea` for next new ticker
3. Replace manual skill chains with appropriate commands
4. Extend with custom commands for your specific patterns

---

**Version**: 1.0 (2025-01-05)
**Compatible with**: Framework v1.0
