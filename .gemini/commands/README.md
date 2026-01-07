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
