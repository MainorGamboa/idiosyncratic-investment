---
name: analyze
description: Run a ticker through full framework analysis from kill screens through scoring. Creates watchlist file with complete evaluation. Use when analyzing a new investment idea, when an event is triggered, or when revisiting a watchlist item.
---

# Analyze Skill

## Purpose
Run a ticker through the full framework analysis, from kill screens through scoring.

## When to Use
- New idea discovered
- Event triggered
- Revisiting watchlist item

## Inputs
```json
{
  "ticker": "SRPT",
  "archetype": "pdufa",
  "event_id": "EVT-2025-001",
  "thesis": "Brief thesis statement"
}
```

## Process

### Step 1: Gather Context
- Current price
- Market cap
- Sector
- Relevant dates

### Step 2: Run Kill Screens
Reference: `schema/kill_screens.json`

For the archetype, check ALL applicable kill screens:
- All archetypes: M-Score, Z-Score
- Merger Arb: Hostile deal, Spread < 2.5%
- Legislative: Macro conflict

**If ANY kill screen fails → PASS. Stop here.**

### Step 3: Create Watchlist File
If screens pass, create `universe/watchlist/{TICKER}.md`:

```markdown
# {TICKER} — {Company Name}

## Status: Investigating
**Archetype:** {archetype}
**Event:** {event_id or "None"}
**Created:** {date}

## Thesis (2 minutes)
{thesis}

## Kill Screens
- [x] M-Score: {value} (PASS)
- [x] Z-Score: {value} (PASS)
- [x] Other applicable screens...

## Key Questions
- [ ] Question 1
- [ ] Question 2

## Quick Take
Initial assessment...

## Links
- [Filing](...)
- [Source](...)
```

### Step 4: Log Screening Result
Update `universe/screened/{YYYY-MM}.json`:

```json
{
  "date": "2025-01-15",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "kill_screens_passed": true,
  "result": "watchlist"
}
```

## Output
```json
{
  "passed_screens": true,
  "watchlist_file": "universe/watchlist/SRPT.md",
  "next_step": "Run 'score' skill to complete analysis"
}
```

## Rules
- ALWAYS run kill screens BEFORE any scoring
- Use exact thresholds from schema
- Document ALL kill screen values, even passes
- If archetype unclear, ask before proceeding

## Related Skills
- `screen` — Kill screens only (faster)
- `score` — Full scoring (after analyze)
