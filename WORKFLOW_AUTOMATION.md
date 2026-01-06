# Autonomous Trading Workflow

## Philosophy

The system uses **autonomous agent execution** with **3 simple commands**:
- `/daily` - Complete daily trading cycle
- `/weekly` - Complete weekly review
- `/analyze TICKER` - Manual ticker analysis

The agent makes decisions automatically based on framework rules. No user intervention required.

---

## Command Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS COMMANDS                           │
│                  (.claude/commands/*.md)                         │
│                                                                   │
│  /daily  →  Full cycle: regime → monitor → scan → analyze       │
│  /weekly →  Review + deep scan + maintenance                     │
│  /analyze → Manual ticker override                               │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  SKILLS LAYER   │  (Autonomous decision-making)
    │ (.codex/skills) │  - Auto-close if exit ≥2.0
    │                 │  - Auto-open if score ≥8.25
    │                 │  - Respect max_positions limit
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   DATA LAYER    │
    │ (schema/*.json) │  - Kill screens
    │ (CONFIG.json)   │  - Scoring rules
    │                 │  - Exit protocols
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  FILE OUTPUTS   │
    │ (trades/, logs/)│  - Active positions
    │ (universe/)     │  - Watchlist
    │ (precedents/)   │  - Patterns
    └─────────────────┘
```

---

## Daily Autonomous Cycle (`/daily`)

```
START
  │
  ├─► 1. REGIME UPDATE
  │   └─► regime skill → Update CONFIG.json (VIX, credit spreads)
  │
  ├─► 2. MONITOR & AUTO-CLOSE
  │   └─► monitor skill → Check active trades
  │       │
  │       └─► If exit signal ≥2.0:
  │           └─► close skill (auto-close, create post-mortem)
  │
  ├─► 3. SCAN NEW EVENTS
  │   └─► scan skill → FDA, SEC 13D, mergers, spin-offs
  │       └─► Update universe/events.json
  │
  ├─► 4. PROCESS EVENTS PIPELINE (Token-efficient: 2-3 events/day)
  │   │
  │   └─► For each unanalyzed event:
  │       │
  │       ├─► screen skill → Kill screens
  │       │   ├─ FAIL → Log to trades/passed/, SKIP
  │       │   └─ PASS → Continue
  │       │
  │       ├─► analyze skill → Create watchlist/TICKER.md
  │       │
  │       ├─► score skill → Calculate score
  │       │   │
  │       │   ├─ Score <6.5 (PASS) → Log to trades/passed/
  │       │   │
  │       │   ├─ Score 6.5-8.24 (CONDITIONAL) → Log to trades/conditional/
  │       │   │
  │       │   └─ Score ≥8.25 (BUY) → Continue to open
  │       │
  │       └─► open skill (if BUY + under max_positions)
  │           └─► Create trades/active/TRD-*.json
  │               Submit entry order
  │
  └─► 5. DAILY SUMMARY
      ├─► Regime state
      ├─► Positions opened today
      ├─► Positions closed today
      ├─► Active positions (X/10)
      ├─► New events discovered
      └─► Alerts requiring attention
```

**Key Design Points:**
- **Incremental**: Processes 2-3 events per day (token-efficient)
- **Autonomous**: Auto-opens BUY scores, auto-closes exit signals
- **Protected**: Respects max_positions limit from CONFIG.json
- **Complete**: Full cycle from scan to close

---

## Weekly Review Cycle (`/weekly`)

```
START
  │
  ├─► 1. PERFORMANCE REVIEW
  │   └─► review skill
  │       ├─► Analyze closed trades this week
  │       ├─► Calculate win rate, avg return, P&L
  │       ├─► Extract lessons learned
  │       └─► Update precedents/patterns.md
  │
  ├─► 2. DEEP CATALYST SCAN
  │   └─► scan skill (comprehensive, 90-day forward)
  │       ├─► FDA PDUFA calendar
  │       ├─► SEC 13D filings (last 7 days)
  │       ├─► Merger/spin-off announcements
  │       ├─► Legislative developments
  │       └─► Goal: 8-12 active catalyst events
  │
  ├─► 3. WATCHLIST MAINTENANCE
  │   ├─► Check stale items (>7 days old)
  │   ├─► Re-score if material news
  │   └─► Archive outdated events
  │
  ├─► 4. PRECEDENT INDEX UPDATE
  │   ├─► Verify precedents/index.json current
  │   ├─► Add tags from closed trades
  │   └─► Update patterns.md
  │
  ├─► 5. FRAMEWORK CALIBRATION
  │   ├─► Review kill screen effectiveness
  │   ├─► Check scoring threshold accuracy
  │   └─► Flag systematic issues
  │
  └─► 6. WEEKLY SUMMARY
      ├─► Week's performance metrics
      ├─► New catalysts added
      ├─► Active positions status
      ├─► Regime changes
      └─► Action items for next week
```

---

## Manual Ticker Analysis (`/analyze TICKER`)

```
START: User provides TICKER
  │
  ├─► screen skill → Kill screens
  │   ├─ FAIL → Log to trades/passed/, EXIT
  │   └─ PASS → Continue
  │
  ├─► analyze skill → Create watchlist
  │
  ├─► score skill → Calculate score
  │   │
  │   ├─ <6.5 (PASS) → Log, EXIT
  │   ├─ 6.5-8.24 (CONDITIONAL) → Log to trades/conditional/
  │   └─ ≥8.25 (BUY) → Continue
  │
  └─► open skill (if BUY + under max_positions)
      └─► Create active trade
```

**Use only when**: User has specific ticker idea outside automated daily flow.

---

## Token Efficiency Strategy

### Daily Incremental Processing

Instead of analyzing all 12 events in one day (expensive), process incrementally:

**Week 1:**
- Day 1: Scan finds 8 events → Analyze 2 → Open 1 BUY
- Day 2: Scan finds 2 more → Analyze 3 total → Open 1 BUY
- Day 3: Analyze remaining 3 → Open 1 BUY
- Day 4-5: Maintenance, monitor existing, scan for new

**Week 2:**
- Day 1: New scans + monitor existing + close exits
- Continue building coverage

**Result**: Over 2 weeks, full coverage achieved with manageable token usage per day.

### Max Positions Limit

CONFIG.json: `max_positions: 10`

Agent stops opening new positions when limit reached. This prevents:
- Over-trading
- Excessive token usage
- Portfolio concentration risk

---

## Autonomous Decision Rules

### Auto-Close Rules
- Exit signal ≥2.0 → **CLOSE** immediately
- Exit signal ≥3.0 → **CLOSE** immediately (full exit)
- Cockroach Rule triggered → **CLOSE** immediately
- Thesis Break → **CLOSE** immediately

### Auto-Open Rules
- Score ≥8.25 (BUY) → **OPEN** position
- Current positions < max_positions → **ALLOW**
- Current positions ≥ max_positions → **SKIP** (log to alerts)

### Logging Rules
- Score <6.5 (PASS) → Log to `trades/passed/`
- Score 6.5-8.24 (CONDITIONAL) → Log to `trades/conditional/`
- Kill screen fail → Log to `trades/passed/`

**No user intervention needed** - agent follows rules autonomously.

---

## Usage Patterns

### Daily Routine
```bash
# Every market day, 9:00 AM
/daily

# Agent handles:
# - Regime update
# - Close exit signals
# - Scan new events
# - Analyze 2-3 events
# - Open BUY positions
# - Report summary
```

### Weekly Routine
```bash
# Friday 4:30 PM or Sunday evening
/weekly

# Agent handles:
# - Performance review
# - Deep catalyst scan
# - Watchlist maintenance
# - Precedent updates
# - Framework calibration
```

### Manual Override
```bash
# Only when you have specific ticker idea
/analyze SRPT

# Agent handles:
# - Kill screens
# - Analysis
# - Scoring
# - Auto-open if BUY
```

---

## Benefits of Autonomous Design

1. **Simplicity**: 3 commands vs 8 (67% reduction)
2. **Autonomous**: Agent makes framework-based decisions
3. **Token-efficient**: Incremental daily processing
4. **Complete coverage**: Nothing missed over time
5. **Protected**: max_positions prevents overtrading
6. **Traceable**: All decisions logged
7. **Scalable**: Works with agent token limits

---

## File Organization

### Automated by `/daily`
```
trades/
├── active/              # Auto-created when score ≥8.25
├── passed/              # Auto-logged when score <6.5 or kill fail
└── conditional/         # Auto-logged when score 6.5-8.24

universe/
├── events.json          # Auto-updated by scan
└── watchlist/           # Auto-created by analyze

logs/
└── */YYYY-MM-DD.log     # Auto-logged by each skill
```

### Automated by `/weekly`
```
precedents/
├── index.json           # Auto-updated from closed trades
└── patterns.md          # Auto-updated with lessons

trades/closed/
├── wins/                # Auto-created by close skill
└── losses/              # Auto-created by close skill
```

---

## Extension Points

### Customize Decision Rules

Edit `.claude/commands/daily.md`:
```markdown
- If score ≥8.5 (BUY): Auto-open position  # Raised from 8.25
- If score ≥2.5: Auto-close               # Raised from 2.0
```

### Adjust Token Budget

Edit daily processing limit:
```markdown
Process Events Pipeline (Token-efficient: 4-5 events/day)  # Raised from 2-3
```

### Add Data Sources

Edit scan step:
```markdown
3. **Discover New Events**
   - Scan FDA PDUFA calendar
   - Scan SEC 13D filings
   - [NEW] Scan earnings calendars
   - Update universe/events.json
```

---

**Version**: 2.0 (Autonomous Agent Design)
**Framework**: v1.0 compatible
**Design**: Token-efficient, fully autonomous, 3-command system
