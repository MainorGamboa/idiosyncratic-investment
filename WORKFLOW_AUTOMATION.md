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

### 1. Discovery Workflow (`/discover`)

```
START
  │
  └─► scan skill ─────────► Find new catalysts
                             │
                             ├─► FDA PDUFA calendar
                             ├─► SEC 13D filings (activists)
                             ├─► Merger announcements (8-K)
                             ├─► Spin-off announcements
                             └─► Legislative developments
                             │
                             ▼
                        Update universe/events.json
                             │
                             ▼
                        Display new events by archetype
                             │
                             ▼
                        Prompt: "Analyze TICKER?"
                             │
                             └─ YES ──► /analyze-idea TICKER or /new-trade TICKER
```

**Output**: Updated events.json, list of new catalysts to investigate

---

### 2. Daily Morning Routine (`/daily`)

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

### 3. Analysis Only (`/analyze-idea TICKER`)

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

**Output**: Watchlist file, scored analysis (NO position opened automatically)

**Use when**: Want to analyze without committing to open position yet

---

### 4. Complete Trade Workflow (`/new-trade TICKER`)

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
  │                       │                   EXIT WORKFLOW
  │                       │
  │                       ├─ 6.5-8.24 (CONDITIONAL) ──► Ask user confirmation
  │                       │                              │
  │                       │                              ├─ NO ──► Log to trades/conditional/
  │                       │                              │          EXIT WORKFLOW
  │                       │                              │
  │                       │                              └─ YES ──► Continue to open
  │                       │
  │                       └─ ≥8.25 (BUY) ──► Auto-proceed to open
  │
  ├─► open skill ──────► Create position
  │                       │
  │                       ├─► Calculate position size (Kellner + Kelly)
  │                       ├─► Create trades/active/TRD-*.json
  │                       ├─► Submit limit order (bid/ask midpoint)
  │                       └─► Display trade confirmation
  │
  └─► Display summary ─► Trade ID, size, entry, exit plan
```

**Output**: Active trade in trades/active/, entry order submitted

**Use when**: Ready to go from idea to open position in one command

---

### 5. Open Position from Watchlist (`/open-position TICKER`)

```
START: TICKER provided
  │
  ├─► Check watchlist ─► Verify universe/watchlist/TICKER.md exists
  │                       │
  │                       └─ NOT FOUND ──► Error: "Run /analyze-idea first"
  │                                         EXIT WORKFLOW
  │
  ├─► Read score ──────► Get score from watchlist file
  │                       │
  │                       ├─ <6.5 ──► Error: "PASS score, cannot open"
  │                       │            EXIT WORKFLOW
  │                       │
  │                       ├─ 6.5-8.24 (CONDITIONAL) ──► Ask user confirmation
  │                       │                              │
  │                       │                              └─ NO ──► EXIT WORKFLOW
  │                       │
  │                       └─ ≥8.25 (BUY) ──► Proceed
  │
  ├─► open skill ──────► Create position (same as /new-trade)
  │
  └─► Display summary ─► Trade ID, size, entry, exit plan
```

**Output**: Active trade in trades/active/, entry order submitted

**Use when**: Already analyzed with `/analyze-idea`, now ready to open

---

### 6. Quick Status Check (`/quick-check`)

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

### 7. Weekly Review (`/weekly-review`)

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

### 8. Close Position (`/close-trade TRADE_ID`)

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
/new-trade SRPT              # Go from idea → position
# OR
/analyze-idea SRPT           # Just analyze first
/open-position SRPT          # Open later if you like it

# Afternoon (exit signal triggered)
/close-trade TRD-20250105-SRPT-PDUFA

# Intraday check (after VIX spike)
/quick-check
```

### Weekly Pattern

```bash
# Friday after market close OR Sunday evening
/weekly-review               # Performance review
/discover                    # Find new catalysts for next week
```

## Manual vs Automated

| Task | Manual Method | Automated Method |
|------|---------------|------------------|
| Find catalysts | `/skill scan` | `/discover` |
| Morning routine | `/skill regime` then `/skill monitor` | `/daily` |
| Analyze idea (no position) | `/skill screen TICKER` → `/skill analyze TICKER` → `/skill score TICKER` | `/analyze-idea TICKER` |
| Idea → Position | Screen → Analyze → Score → Open (4 skills) | `/new-trade TICKER` |
| Open from watchlist | `/skill open TICKER` | `/open-position TICKER` |
| Check status | Read CONFIG, check alerts, monitor | `/quick-check` |
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
