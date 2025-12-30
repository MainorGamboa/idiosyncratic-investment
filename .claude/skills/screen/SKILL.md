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

### Step 2: Run Each Screen
For each applicable screen:
1. Gather required data (financials, deal terms, etc.)
2. Calculate or verify metric
3. Compare to threshold
4. If ANY screen fails → STOP and return FAIL

### Step 3: Log Result
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
