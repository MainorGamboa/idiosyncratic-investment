# Review Skill

## Purpose
Generate weekly review report. Summarizes active trades, closed trades, pass decisions, regime changes, and lessons learned.

## When to Use
- End of each week (Sunday evening or Monday morning)
- End of month (more comprehensive)
- After significant market events
- Quarterly (deep analysis)

## Inputs
```json
{
  "period": "week",
  "date_range": {
    "start": "2025-01-06",
    "end": "2025-01-12"
  }
}
```

**Parameters:**
- `period` (optional): "week" | "month" | "quarter" (defaults to "week")
- `date_range` (optional): Specific date range (defaults to past week)

## Process

### Step 1: Identify Week Number
Calculate ISO week number: `{YYYY}-W{NN}`

Example: `2025-W02`

### Step 2: Gather Data

#### Active Trades
- Load all `trades/active/*.json`
- For each trade: current P&L, days held, last monitoring update
- Calculate total exposure, concentration by archetype

#### Closed Trades (this period)
- Filter `trades/closed/*.json` by exit_date within date_range
- Aggregate: total return, win rate, average hold time
- Group by archetype, exit reason

#### Pass Decisions (this period)
- Filter `trades/passed/*.json` by decision_date within date_range
- Count by archetype, reason for pass
- Note any validated passes (where stock indeed moved against thesis)

#### Screened Ideas
- Load `universe/screened/{YYYY-MM}.json` for this period
- Count: total screened, passed, failed
- Failed by: which kill screen

#### Regime Changes
- Load `CONFIG.json` regime history (if tracked)
- Note any VIX spikes, credit spread changes
- Actions taken in response

#### Events Completed
- Filter `universe/events.json` for events with status "completed" in this period
- Were they traded? Outcomes?

### Step 3: Calculate Key Metrics

**Portfolio Level:**
- Total exposure (sum of all active positions)
- Number of active positions
- Largest position size
- Archetype concentration

**Performance (closed trades only):**
- Win rate: % of profitable trades
- Average return: mean of all returns
- Average winner vs average loser
- Best trade, worst trade
- Total P&L for period

**Activity:**
- Ideas screened
- Positions opened
- Positions closed
- Events tracked

**Calibration:**
- Score vs outcome correlation
- Did high-score (≥8.25) trades outperform?
- Did passes prove correct?

### Step 4: Extract Lessons Learned
From closed trade post-mortems:
- New patterns discovered
- Rules that worked well
- Rules that failed
- Suggested adjustments

### Step 5: Generate Review Document
Create `journal/reviews/{YYYY-WNN}.md`:

```markdown
# Weekly Review — Week 2, 2025
**Period:** Jan 6 - Jan 12, 2025

## Summary
- Active Positions: 3 (exposure: 8.5% of portfolio)
- Closed Trades: 1 (+39.4% return, 37 days)
- New Ideas Screened: 5 (3 passed, 2 failed)
- Regime: Stable (VIX 18.5, HY OAS 340bps)

## Active Trades

| Trade ID | Ticker | Archetype | Entry | Current | P&L | Days |
|----------|--------|-----------|-------|---------|-----|------|
| TRD-2025-002 | XYZ | Merger Arb | $45.00 | $47.50 | +5.6% | 14 |
| TRD-2025-003 | ABC | Activist | $32.00 | $33.20 | +3.8% | 7 |
| TRD-2025-004 | DEF | PDUFA | $18.50 | $19.10 | +3.2% | 3 |

**Total Exposure:** 8.5% (within limits)
**Archetype Breakdown:** Merger (3%), Activist (3.5%), PDUFA (2%)

**Monitoring Notes:**
- TRD-2025-002: Spread tightening as expected, close date Feb 28
- TRD-2025-003: Tier-1 activist filed 13D, settlement likely
- TRD-2025-004: PDUFA date March 15, no news this week

## Closed Trades

### TRD-2025-001: SRPT (PDUFA)
- **Entry:** $125.50, Jan 10
- **Exit:** $175.00, Feb 16
- **Return:** +39.4% (37 days)
- **Outcome:** FDA approval as expected
- **Lessons:** Breakthrough + AdCom combo is high-conviction (score 8.5 validated)

**Period Performance:**
- Win Rate: 100% (1/1)
- Average Return: +39.4%
- Total P&L: +$1,485

## Ideas Screened

| Ticker | Archetype | Result | Reason |
|--------|-----------|--------|--------|
| SRPT | PDUFA | PASS | All screens passed, scored 8.5 → BUY |
| INTC | Legislative | FAIL | Obvious beneficiary (CHIPS Act) |
| ENPH | Legislative | FAIL | Macro conflict (rate sensitive) |
| GHI | Merger Arb | PASS | Screens passed, spread 6.5% |
| JKL | PDUFA | PASS | Screens passed, pending scoring |

**Kill Screen Summary:**
- Passed: 3/5 (60%)
- Failed: 2/5
  - Obvious beneficiary: 1
  - Macro conflict: 1

## Regime Analysis

**Current Regime:** Stable
- VIX: 18.5 (range: 15-20)
- HY OAS: 340bps (stable)
- Action: Normal operations

**Changes This Week:** None

## Lessons Learned

### What Worked
1. **Breakthrough + AdCom pattern** validated (TRD-2025-001, +39%)
2. **Kill screens** prevented likely losers (INTC, ENPH both declined this week)
3. **Position sizing** appropriate (1.5% for PDUFA despite asymmetry)

### What Didn't Work
- None this period (small sample)

### Adjustments Considered
- When score >8.5 AND multiple confirming patterns, consider maxing archetype size
- Continue tracking "obvious beneficiary" pattern (both screened ideas declined)

## Upcoming Catalysts (Next 2 Weeks)

| Event ID | Ticker | Catalyst | Date | Status |
|----------|--------|----------|------|--------|
| EVT-2025-002 | XYZ | Merger close | Jan 28 | Tracking |
| EVT-2025-005 | MNO | PDUFA decision | Jan 30 | Not yet analyzed |

## Action Items
- [ ] Monitor XYZ merger close (Jan 28)
- [ ] Analyze MNO PDUFA event before Jan 30
- [ ] Run regime check Monday morning
- [ ] Review ABC activist settlement progress

---

*Review completed: 2025-01-13*
*Next review: 2025-01-20*
```

## Output
```json
{
  "review_file": "journal/reviews/2025-W02.md",
  "period": "2025-01-06 to 2025-01-12",
  "summary": {
    "active_positions": 3,
    "closed_trades": 1,
    "win_rate": 1.0,
    "average_return": 0.394,
    "total_pnl": 1485,
    "ideas_screened": 5,
    "new_lessons": 3
  }
}
```

## Rules
- Always review at same interval (weekly preferred)
- Include both wins AND losses (be honest)
- Extract specific, actionable lessons
- Don't cherry-pick data
- Compare score predictions vs actual outcomes
- Track regime impact on performance
- Note patterns that are working/failing

## Review Depth by Period

### Weekly
- Active trades status
- Closed trades analysis
- Screening activity
- Key lessons

### Monthly
- All of weekly, plus:
- Archetype performance comparison
- Score calibration analysis
- Pattern effectiveness
- Rule adjustments needed

### Quarterly
- All of monthly, plus:
- Framework performance vs benchmark
- Sharpe ratio calculation
- Win rate by score bucket
- Base rate validation
- Major rule changes (if any)

## Calibration Analysis (Monthly/Quarterly)

Compare score buckets vs outcomes:

| Score Range | Trades | Win Rate | Avg Return |
|-------------|--------|----------|------------|
| 9.0+ | 5 | 80% | +28% |
| 8.25-8.99 | 12 | 67% | +18% |
| 6.5-8.24 | 8 | 50% | +8% |
| <6.5 (PASS) | 15 | 25% | -12% |

**Validation:** High scores should correlate with better outcomes.

## Related Skills
- `monitor` — Provides data on active positions
- `close` — Post-mortems feed into lessons learned
- `search` — Find historical comparisons
- `regime` — Include regime analysis in review
