---
name: score
description: Complete 6-filter scoring to generate BUY/CONDITIONAL/PASS decision. Updates watchlist with complete scoring breakdown. Use after analyze skill has created watchlist file and kill screens have passed.
---

# Score Skill

## Purpose
Complete 6-filter scoring after initial analysis. Generates final BUY/CONDITIONAL/PASS decision.

## When to Use
- After `analyze` skill has created watchlist file
- Kill screens have already passed
- Ready to make final decision on idea

## Inputs
```json
{
  "ticker": "SRPT",
  "thesis": "PDUFA with positive AdCom, breakthrough therapy designation. Market pricing ~70% approval, estimate 85%.",
  "archetype": "pdufa"
}
```

**Parameters:**
- `ticker` (required): Stock symbol
- `thesis` (required): Brief thesis statement (2-3 sentences)
- `archetype` (required): One of 7 archetypes

## Process

### Step 1: Score Each Filter
Reference: `schema/scoring.json`

Score each of the 6 filters (0 to max_points):

| Filter | Max Points | Question |
|--------|------------|----------|
| Catalyst | 2 | Defined event with known timeline? |
| Mispricing | 2 | Gap between price and fair value? |
| Noise Survival | 2 | Can survive volatility until catalyst? |
| Downside Floor | 2 | Asset value if thesis fails? |
| Risk/Reward | 2 | 3:1 = 2pts, 2:1 = 1pt |
| Info Half-Life | 1 | Edge persists through catalyst? |

**Scoring Guidelines:**
- 2 pts = Strong/clear
- 1.5 pts = Good but not perfect
- 1 pt = Moderate
- 0.5 pts = Weak
- 0 pts = Absent

### Step 2: Apply Adjustments
Reference: `schema/scoring.json` and `schema/archetypes.json`

**Activist Adjustments:**
- Tier-1 (Elliott, Starboard, ValueAct, Pershing): +1.0
- Tier-2 (Trian, Icahn, Third Point): +0.5
- Tier-3 (Others): +0

**Legislative Adjustments:**
- Obvious beneficiary: -1.5
- Macro-sensitive: -1.0

**Merger Adjustments:**
- Third-party veto: -1.0
- DOJ/FTC lawsuit: -2.0

### Step 3: Calculate Final Score
```
base_score = sum(filter_scores)
final_score = base_score + adjustments
```

### Step 4: Determine Decision
Reference: `schema/scoring.json` thresholds

- `final_score >= 8.25` → **BUY**
- `6.5 <= final_score < 8.25` → **CONDITIONAL**
- `final_score < 6.5` → **PASS**

### Step 5: Update Watchlist File
Update `universe/watchlist/{TICKER}.md` with scoring section:

```markdown
## Scoring (Final: 8.5)

### Filter Scores
- **Catalyst:** 2.0 — FDA PDUFA date Feb 15, hard date
- **Mispricing:** 1.5 — Market 70%, estimate 85% (15% gap)
- **Noise Survival:** 1.5 — Biotech with cash runway through catalyst
- **Downside Floor:** 1.0 — Pre-approval value ~$95
- **Risk/Reward:** 1.5 — 2.5:1 (target $180, entry $125, floor $95)
- **Info Half-Life:** 1.0 — Edge persists until PDUFA date

**Base Score:** 8.5

### Adjustments
None applicable

**Final Score:** 8.5

### Decision: BUY
Score 8.5 exceeds threshold 8.25. High conviction setup.
```

## Output
```json
{
  "ticker": "SRPT",
  "score": 8.5,
  "breakdown": {
    "catalyst": 2.0,
    "mispricing": 1.5,
    "noise_survival": 1.5,
    "downside_floor": 1.0,
    "risk_reward": 1.5,
    "info_half_life": 1.0,
    "base_score": 8.5,
    "adjustments": [],
    "final_score": 8.5
  },
  "decision": "BUY",
  "threshold_met": "8.25",
  "next_step": "Run 'open' skill to create position"
}
```

## Rules
- Always score ALL 6 filters (don't skip any)
- Use schema/scoring.json for exact point values
- Document reasoning for each filter score
- Apply all relevant adjustments
- Update watchlist file with complete scoring breakdown
- PASS decisions should still be documented (helps calibration)

## Scoring Calibration Tips

**Catalyst (max 2):**
- 2.0 = Hard date, binary event, no delays expected
- 1.5 = Soft date or potential delays
- 1.0 = Timeline uncertain
- 0.5 = Catalyst timing vague

**Mispricing (max 2):**
- 2.0 = >20% gap between price and fair value
- 1.5 = 15-20% gap
- 1.0 = 10-15% gap
- 0.5 = 5-10% gap

**Risk/Reward (max 2):**
- 2.0 = 3:1 or better
- 1.5 = 2.5:1
- 1.0 = 2:1
- 0.5 = 1.5:1

## Related Skills
- `analyze` — Creates watchlist (run before score)
- `open` — Opens position (run after BUY decision)
- `search` — Find precedents for calibration
