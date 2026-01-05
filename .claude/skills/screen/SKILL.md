---
name: screen
description: Apply kill screens only for quick pass/fail check. Faster than full analyze. Use for quick validation of new ideas, batch screening of multiple tickers, or pre-filtering before deeper analysis.
---

# Screen Skill

## Purpose
Apply kill screens only (faster than full analyze). Quick pass/fail check before deeper analysis.

## When to Use
- Quick validation of new idea before investing time in full analysis
- Batch screening of multiple tickers
- Pre-filter before running analyze skill

## Inputs
```json
{
  "ticker": "SRPT",
  "archetype": "pdufa"
}
```

**Parameters:**
- `ticker` (required): Stock symbol to screen
- `archetype` (optional): If known, only run screens applicable to that archetype

## Process

### Step 1: Identify Applicable Kill Screens
Reference: `schema/kill_screens.json`

**All Archetypes:**
- Beneish M-Score
- Altman Z-Score

**Merger Arb Only:**
- Hostile Deal
- Merger Spread

**Legislative Only:**
- Macro Conflict

### Step 2: Gather Data with Fallback

**Data Source Strategy** (see TECHNICAL_SPEC.md §2.1):

**Financials** (from CONFIG.json data_sources.financials_priority):
1. SEC API: `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
2. If fails → Manual calculation from 10-Q/10-K
3. If fails → Third-party screening tools
4. If all fail → Log error, notify user, halt

**Data Validation** (see TECHNICAL_SPEC.md §2.2):
- M-Score expected range: -2 to +2 (flag if >10 or <-10, try alternative)
- Z-Score expected range: -5 to +10 (flag extreme outliers)
- Strict threshold enforcement: 1.79 < 1.81 = FAIL (no tolerance)

### Step 3: Run Each Screen
For each applicable screen:
1. Gather required data (with fallback strategy above)
2. Validate data for anomalies
3. Calculate or verify metric
4. Compare to threshold
5. If ANY screen fails → STOP and return FAIL

### Step 4: Log Result
Update `universe/screened/{YYYY-MM}.json`:

```json
{
  "date": "2025-01-15",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "kill_screens_passed": true,
  "screens_checked": ["beneish_m_score", "altman_z_score"],
  "results": {
    "beneish_m_score": {"value": -2.1, "threshold": -1.78, "passed": true},
    "altman_z_score": {"value": 2.5, "threshold": 1.81, "passed": true}
  }
}
```

### Step 5: Write Log Entry

Append to `logs/screen/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T11:20:00Z",
  "skill": "screen",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "outcome": "PASS",
  "metrics": {
    "m_score": -2.1,
    "z_score": 2.5,
    "kill_screens_passed": true
  },
  "data_sources": ["SEC API"],
  "execution_time_ms": 950,
  "notes": "Quick screen passed. Ready for full analyze."
}
```

Log every execution for audit trail and performance tracking.

## Output
```json
{
  "passed": true,
  "failed_screens": [],
  "reason": "All kill screens passed",
  "next_step": "Run 'analyze' skill for full framework analysis"
}
```

**If failed:**
```json
{
  "passed": false,
  "failed_screens": ["beneish_m_score"],
  "reason": "M-Score -1.5 exceeds threshold -1.78 (manipulation risk)",
  "recommendation": "PASS on this idea"
}
```

## Rules
- ANY kill screen fail = automatic PASS
- Always check ALL applicable screens (don't stop at first fail for logging purposes)
- Use exact thresholds from schema/kill_screens.json
- Log all screening attempts to screened/ directory
- Hostile deals and narrow spreads (<2.5%) are automatic fails for merger arb

## Kill Screen Thresholds Quick Reference

| Screen | Threshold | Operator | Fail Condition |
|--------|-----------|----------|----------------|
| M-Score | -1.78 | > | M-Score > -1.78 |
| Z-Score | 1.81 | < | Z-Score < 1.81 |
| Hostile | N/A | == | Deal is hostile |
| Spread | 2.5% | < | Spread < 2.5% |
| Macro Conflict | N/A | manual | Rate/commodity conflicts with thesis |

## Related Skills
- `analyze` — Full framework analysis (includes kill screens + watchlist creation)
- `score` — 6-filter scoring (only run after screens pass)
