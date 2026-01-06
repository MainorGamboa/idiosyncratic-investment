# Autonomous Trading Commands

This system uses **3 simple commands** to run the entire trading operation autonomously.

## The 3 Commands

### 1. `/daily` - Complete Daily Cycle

**Runs everything automatically:**
- Update market regime (VIX, credit)
- Monitor & auto-close positions with exit signals
- Scan for new catalyst events
- Analyze new events → score → auto-open BUY positions
- Generate daily summary

**When**: Every market day before 9:30 AM ET

**Token-efficient**: Processes 2-3 events per day, builds coverage incrementally

---

### 2. `/weekly` - Complete Weekly Review

**Runs everything automatically:**
- Performance review (wins, losses, patterns)
- Deep catalyst scan (90-day forward look)
- Watchlist maintenance (re-score stale items)
- Precedent index updates
- Framework calibration check

**When**: Friday after close OR Sunday evening

---

### 3. `/analyze TICKER` - Manual Ticker Analysis

**For specific ideas outside automated flow:**
- Kill screens → Analyze → Score → Auto-open if BUY
- Only needed when YOU have a ticker idea

**Example**: `/analyze SRPT`

---

## How It Works

### Daily Pattern
```bash
# Every morning
/daily
# That's it. The agent handles everything.
```

The `/daily` command:
1. Updates regime
2. Closes positions with exit signals (≥2.0)
3. Scans for new catalysts
4. Analyzes 2-3 new events (token-efficient)
5. Opens BUY positions (respects max_positions limit from CONFIG.json)
6. Reports summary

**No user decisions needed** - fully autonomous.

### Weekly Pattern
```bash
# Friday or Sunday
/weekly
# Reviews performance, scans deep, maintains watchlist
```

### Manual Override
```bash
# Only when you have a specific ticker idea
/analyze SRPT
```

---

## Philosophy: Autonomous Agent

**Old approach**: 8 commands, user decides every step
**New approach**: 3 commands, agent decides autonomously

### Decision Rules (Built-in)

- **Auto-close**: Exit signal ≥2.0 → close position immediately
- **Auto-open**: Score ≥8.25 (BUY) → open position (if under max_positions)
- **Log CONDITIONAL**: Score 6.5-8.24 → log to trades/conditional/ for review
- **Log PASS**: Score <6.5 OR kill screen fail → log to trades/passed/

### Token Management

Daily command processes incrementally:
- **Day 1**: 3 events scanned, 2 analyzed, 1 opened
- **Day 2**: 3 more events, continue building
- **Day 3+**: Maintain coverage, add new events

Over weeks, full coverage builds up.

### Max Positions Protection

CONFIG.json has `max_positions: 10` - agent respects this automatically.

---

## Benefits

1. **Simple**: 3 commands vs 8
2. **Autonomous**: Agent makes decisions, not user
3. **Token-efficient**: Incremental processing over days
4. **Complete**: Nothing falls through cracks
5. **Traceable**: Everything logged (passed/, conditional/, active/, closed/)

---

## What Happened to Old Commands?

Removed for simplicity:
- ~~`/analyze-idea`~~ → Use `/analyze TICKER`
- ~~`/new-trade`~~ → Now automatic in `/daily`
- ~~`/open-position`~~ → Now automatic in `/daily`
- ~~`/close-trade`~~ → Now automatic in `/daily`
- ~~`/discover`~~ → Now automatic in `/daily`
- ~~`/quick-check`~~ → Check logs/ or run `/daily`
- ~~`/weekly-review`~~ → Now `/weekly`

**Less commands, more automation.**

---

## Extending

To add custom behavior:
1. Edit `.claude/commands/daily.md` or `weekly.md`
2. Adjust decision rules (e.g., change BUY threshold from 8.25)
3. Add new data sources to scan step

Skills (`.codex/skills/*`) remain unchanged - commands orchestrate them.
