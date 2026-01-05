---
name: search
description: Find similar trades by tags or text query. Enables precedent-based decision making and pattern recognition. Use before scoring new ideas, during post-mortems, or when researching pattern effectiveness.
---

# Search Skill

## Purpose
Find similar trades by tags or text query. Enables precedent-based decision making and pattern recognition.

## When to Use
- Before scoring new idea (find similar precedents)
- During post-mortem (find related trades)
- Researching pattern effectiveness
- Calibrating filter scores based on outcomes

## Inputs
```json
{
  "tags": ["pdufa", "breakthrough_therapy"],
  "query": "AdCom positive",
  "archetype": "pdufa",
  "outcome": "positive"
}
```

**Parameters:**
- `tags` (optional): Array of tags to search for (OR logic)
- `query` (optional): Text search across trade files
- `archetype` (optional): Filter to specific archetype
- `outcome` (optional): Filter by outcome (positive/negative/neutral)

**Note:** Provide at least one of `tags` or `query`.

## Process

### Step 1: Search by Tags (if provided)
Reference: `precedents/index.json`

```javascript
matching_trade_ids = []
for tag in tags:
    if tag in index["tags"]:
        matching_trade_ids.extend(index["tags"][tag])

matching_trade_ids = unique(matching_trade_ids)
```

### Step 2: Search by Query (if provided)
Search all files in `trades/closed/` and `trades/active/`:

```javascript
grep -r "query" trades/closed/*.json trades/active/*.json
```

Extract trade_ids from matching files.

### Step 3: Combine Results
If both tags and query provided, take intersection (AND logic).

### Step 4: Apply Filters
If `archetype` provided, filter to trades with matching archetype.
If `outcome` provided, filter to trades with matching outcome.

### Step 5: Load Trade Details
For each matching trade_id:
- Load the trade JSON
- Extract key fields: ticker, archetype, score, outcome, tags

### Step 6: Sort by Relevance
Sort by:
1. Number of matching tags (descending)
2. Outcome relevance (positive/negative)
3. Date (most recent first)

### Step 7: Write Log Entry

Append to `logs/search/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T18:00:00Z",
  "skill": "search",
  "query": "pdufa_approval positive_adcom",
  "outcome": "SUCCESS",
  "metrics": {
    "results_found": 3,
    "tags_searched": ["pdufa_approval", "positive_adcom"]
  },
  "data_sources": ["precedents/index.json"],
  "execution_time_ms": 450,
  "notes": "Found 3 precedents matching query."
}
```

## Output
```json
{
  "query_summary": {
    "tags": ["pdufa", "breakthrough_therapy"],
    "query": "AdCom positive",
    "archetype": "pdufa",
    "matches_found": 3
  },
  "matching_trades": [
    {
      "trade_id": "TRD-2025-001",
      "ticker": "SRPT",
      "archetype": "pdufa",
      "score": 8.5,
      "outcome": {
        "return_pct": 0.394,
        "thesis_correct": true
      },
      "tags": ["pdufa", "breakthrough_therapy", "adcom_positive"],
      "matching_tags": ["pdufa", "breakthrough_therapy"],
      "file": "trades/closed/TRD-2025-001.json"
    },
    {
      "trade_id": "TRD-2024-008",
      "ticker": "SGEN",
      "archetype": "pdufa",
      "score": 8.0,
      "outcome": {
        "return_pct": 0.287,
        "thesis_correct": true
      },
      "tags": ["pdufa", "breakthrough_therapy", "oncology"],
      "matching_tags": ["pdufa", "breakthrough_therapy"],
      "file": "trades/closed/TRD-2024-008.json"
    }
  ],
  "summary": "Found 3 PDUFA trades with breakthrough therapy designation. Average return: 35.2%, Win rate: 100%"
}
```

## Rules
- Search both active and closed trades
- Return up to 20 most relevant matches
- Include summary statistics (avg return, win rate) if multiple matches
- Tag search is OR logic (any tag matches)
- If both tags and query provided, use AND logic (must match both)
- Sort by relevance (most matching tags first)

## Search Examples

### Example 1: Find Activist Tier-1 Trades
```json
{
  "tags": ["activist_tier1"],
  "outcome": "positive"
}
```
→ Returns all successful Tier-1 activist campaigns

### Example 2: Find Legislative Passes
```json
{
  "tags": ["obvious_beneficiary"],
  "archetype": "legislative"
}
```
→ Returns legislative trades that were passed due to obvious beneficiary pattern

### Example 3: Find PDUFA with AdCom
```json
{
  "query": "AdCom",
  "archetype": "pdufa"
}
```
→ Returns all PDUFA trades where AdCom is mentioned

### Example 4: Find Cockroach Exits
```json
{
  "tags": ["cockroach_exit"]
}
```
→ Returns all trades exited due to cockroach rule

## Common Tags

**Archetypes:**
- `merger_arb`, `pdufa`, `activist`, `spinoff`, `liquidation`, `insider`, `legislative`

**Patterns:**
- `obvious_beneficiary`, `macro_conflict`, `activist_tier1`, `breakthrough_therapy`, `adcom_positive`

**Outcomes:**
- `positive_outcome`, `negative_outcome`, `neutral_outcome`

**Exit Reasons:**
- `info_parity_exit`, `cockroach_exit`, `thesis_break`, `stop_loss_exit`

**Special:**
- `pass_validated` — Correct decision to pass
- `exception_taken` — Broke a rule (document why)
- `regime_override` — Regime suggested pause but traded anyway

## Analysis Use Cases

**Calibration:**
```json
{"tags": ["pdufa"], "outcome": "positive"}
```
→ Check if PDUFA scoring is calibrated (score vs outcome)

**Pattern Validation:**
```json
{"tags": ["obvious_beneficiary"]}
```
→ Verify if obvious beneficiary pattern holds (should be negative)

**Archetype Performance:**
```json
{"archetype": "merger_arb", "tags": ["positive_outcome"]}
```
→ Review successful merger arb trades for common factors

## Related Skills
- `close` — Adds tags during post-mortem
- `score` — Use precedents for scoring calibration
- `review` — Include precedent analysis in weekly review
