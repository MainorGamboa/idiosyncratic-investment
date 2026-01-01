---
name: regime
description: Check market regime via VIX and credit spreads. Updates CONFIG.json with regime state and recommended actions. Use daily before market open, after significant market moves, or before opening new positions.
---

# Regime Skill

## Purpose
Check market regime (VIX, credit spreads) and update CONFIG.json with current conditions and recommended actions.

## When to Use
- Daily (morning routine before market open)
- After significant market moves
- Before opening new positions
- When considering risk adjustments

## Inputs
```json
{
  "manual_override": false
}
```

**Parameters:**
- `manual_override` (optional): If true, prompt for manual VIX/spread input instead of fetching

## Process

### Step 1: Fetch Current Market Data

**VIX (CBOE Volatility Index):**
- Fetch current VIX level
- Sources: Yahoo Finance (^VIX), CBOE data, or manual input

**HY OAS (High Yield Option-Adjusted Spread):**
- Fetch current HY OAS spread in basis points
- Sources: FRED (Federal Reserve Economic Data), Bloomberg, or manual input
- Series: FRED code "BAMLH0A0HYM2"

### Step 2: Determine VIX Level and Action
Reference: `FRAMEWORK.md` Regime Overlays

| VIX Range | Level | Action |
|-----------|-------|--------|
| < 15 | Low | Normal operations |
| 15-20 | Normal | Normal operations |
| 20-30 | Elevated | Reduce risk, widen stops |
| > 30 sustained | High | Pause all new merger arb |

### Step 3: Determine Credit Condition

**Baseline HY OAS:**
- Track 30-day moving average
- Note: Baseline varies by economic cycle (typically 300-400 bps)

**Credit Spread Change:**
- If HY OAS widens 100bp+ from baseline → Reduce merger arb proportionally
- If HY OAS stable/tightening → Normal operations

**Credit Condition:**
- `tightening` — OAS decreasing
- `stable` — OAS within 50bp of average
- `widening` — OAS increasing 50-100bp
- `stress` — OAS increasing >100bp

### Step 4: Determine Overall Regime Actions

**Alerts:**
- VIX > 30 sustained → "PAUSE all new merger arb positions"
- VIX 20-30 → "Reduce position sizes by 25%, widen stops by 20%"
- HY OAS +100bp → "Reduce merger arb exposure proportionally"
- Correlation elevated → "Diversify across uncorrelated archetypes"

### Step 5: Update CONFIG.json

Update the `regime` section:

```json
{
  "regime": {
    "vix": 18.5,
    "vix_level": "15-20",
    "vix_action": "Normal operations",
    "hy_oas_bps": 340,
    "hy_oas_baseline": 350,
    "credit_condition": "stable",
    "credit_action": "Normal operations",
    "correlation_elevated": false,
    "alerts": [],
    "last_updated": "2025-01-15T08:00:00Z"
  }
}
```

### Step 6: Check Active Positions (if regime changed)

If regime has shifted to elevated/high:
- List active merger arb positions
- Suggest position size reductions
- Suggest stop tightening

## Output
```json
{
  "regime_updated": true,
  "vix": 18.5,
  "vix_level": "15-20",
  "vix_action": "Normal operations",
  "hy_oas_bps": 340,
  "credit_condition": "stable",
  "alerts": [],
  "action_required": false,
  "summary": "Market regime normal. VIX 18.5, HY spreads stable at 340bps. No position adjustments needed."
}
```

**Example with Alert:**
```json
{
  "regime_updated": true,
  "vix": 32.5,
  "vix_level": ">30",
  "vix_action": "Pause all new merger arb",
  "hy_oas_bps": 485,
  "credit_condition": "stress",
  "alerts": [
    "VIX >30: Pause all new merger arb positions",
    "HY OAS +135bp from baseline: Reduce merger arb exposure",
    "Consider exiting lowest-conviction merger arb positions"
  ],
  "action_required": true,
  "summary": "Market regime STRESSED. VIX 32.5, HY spreads widening significantly. PAUSE new merger arb, review existing positions."
}
```

## Rules
- Run DAILY before market open
- Update CONFIG.json every run (timestamp is critical)
- VIX >30 must be "sustained" (3+ days) before pausing all new positions
- Credit spread changes are relative to 30-day baseline (not absolute levels)
- Alert thresholds are from FRAMEWORK.md (don't modify without updating framework)
- Regime changes should trigger position review via `monitor` skill

## Regime Quick Reference

### VIX Levels
- **<15:** Complacent, watch for mean reversion
- **15-20:** Normal, full framework operations
- **20-30:** Elevated, defensive posture
- **>30:** High stress, pause merger arb

### Credit Spreads
- **<300bps:** Tight, favorable for credit-sensitive strategies
- **300-400bps:** Normal
- **400-500bps:** Widening, caution on merger arb
- **>500bps:** Stress, significantly reduce credit exposure

### Actions by Regime

| VIX | Credit | Action |
|-----|--------|--------|
| <20 | Stable | Full operations |
| 20-30 | Stable | Reduce sizes 25%, widen stops |
| >30 | Stable | Pause merger arb, review all |
| <20 | Stress | Reduce merger arb |
| 20-30 | Stress | Pause merger arb, reduce all sizes |
| >30 | Stress | DEFENSIVE: Tighten stops, exit low-conviction |

## Data Sources

**VIX:**
- Yahoo Finance: `^VIX`
- CBOE: cboe.com/tradable_products/vix
- Manual: Enter current value

**HY OAS:**
- FRED: fred.stlouisfed.org/series/BAMLH0A0HYM2
- Bloomberg: Command `I18146 <Index> DES`
- Manual: Enter current value in basis points

## Related Skills
- `monitor` — Check regime impact on active positions
- `open` — Check regime before opening new positions
- `review` — Include regime analysis in weekly review
