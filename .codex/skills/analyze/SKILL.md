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

### Step 1: Gather Context (AUTOMATED)

**AUTOMATION: Use data_fetcher.py to automatically fetch all required data**

Run the automated data fetcher:
```bash
python scripts/data_fetcher.py fetch_all {TICKER} --industry {industry}
```

This script automatically:
- Fetches current price (tries IBKR → Stooq → Yahoo with graceful degradation)
- Fetches financials from SEC API
- Calculates M-Score and Z-Score with industry adjustments
- Validates data across sources
- Returns formatted data for kill screens

**Example output:**
```json
{
  "ticker": "SRPT",
  "price": 125.50,
  "price_source": "IBKR",
  "market_cap": 8500000000,
  "m_score": -1.23,
  "z_score": 2.1,
  "z_score_threshold": 1.5,
  "industry": "biotech",
  "data_quality": "high"
}
```

**Data Source Strategy** (see TECHNICAL_SPEC.md §2.1):

**Price data** (from CONFIG.json data_sources.price_priority):
1. Try IBKR paper account: `http://127.0.0.1:4002` (real-time)
2. If fails → Stooq: `stooq.com/q/d/l/?s={ticker}.us&i=d` (15min delay)
3. If fails → Yahoo Finance (fallback)
4. If all fail → Log error to `logs/analyze/YYYY-MM-DD.log`, notify user, halt

**Financials** (from CONFIG.json data_sources.financials_priority):
1. SEC API: `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
2. If fails → Manual calculation from 10-Q/10-K
3. If fails → Third-party screening tools

Display fetched data to user:
- Current price (with source attribution)
- Market cap
- M-Score (with validation notes)
- Z-Score (with industry-adjusted threshold)
- Data quality assessment

### Step 2: Run Kill Screens
Reference: `schema/kill_screens.json`

For the archetype, check ALL applicable kill screens:
- **All archetypes**: M-Score, Z-Score, Market cap ceiling
- **Merger Arb**: Hostile deal, Spread < 2.5%
- **Legislative**: Macro conflict
- **Insider** (v1.1): Insider Cluster Quality (KS-008) - requires 3+ opportunistic insiders
  - Routine traders excluded (trades in same month annually for 3+ years)
  - Uses `scripts/insider_analysis.py` to validate cluster
- **PDUFA**: Financial health (18mo cash runway, D/E <0.75, net cash position)

**If ANY kill screen fails → PASS. Stop here.**

### Step 2a: Archetype-Specific Data Gathering (v1.1)

**data_fetcher.py now automatically gathers archetype-specific data:**

**For PDUFA archetype:**
- Check Form 483 with OAI (affects scoring: -1.0pt if present)
- Check EMA approval status (affects scoring: +0.5pt if approved)
- Note: These are scoring modifiers, not kill screens
- Manual verification may be required (see data_fetcher output)

**For Insider archetype:**
- Validate insider cluster quality (kill screen KS-008)
- Fetch 3-year Form 4 history for each insider
- Classify routine vs opportunistic traders
- Count only opportunistic insiders toward 3+ threshold

**For Activist/Spin-off archetypes:**
- Check WARN Act filings (state databases)
- Activist: WARN with "loss of contract" = exit signal (not kill screen)
- Spin-off: WARN at SpinCo = reduce position size 50%

**For Merger Arb:**
- Note: Second request, CFIUS, and China-connected checks happen during scoring
- Not part of kill screens, but tracked for scoring adjustments

### Step 2b: Data Validation & Anomaly Detection

**See TECHNICAL_SPEC.md §2.2 for complete validation protocols.**

**M-Score validation:**
- Expected range: -2 to +2
- If M-Score > 10 OR < -10:
  - Flag as suspicious: "M-Score {value} outside expected range"
  - Try alternative data source
  - If all sources show anomaly, log and notify user

**Price validation:**
- If price < $0.10 OR price_change > 50% in 1 day:
  - Cross-check all sources (IBKR, Stooq, Yahoo)
  - If all sources agree → Accept data
  - If sources conflict → Alert user, use most recent verified price

**Z-Score borderline handling:**
- Strict enforcement: 1.79 < 1.81 threshold = FAIL (no tolerance band)
- Log exact values for reference

### Step 2c: Options Viability Assessment (If Applicable)

**Run After Equity Kill Screens Pass:**

Check if archetype supports options (`schema/options_strategies.json` → archetype.enabled):

1. **Fetch Options Chain Data**
   - Query IBKR or Yahoo Finance for options chain
   - Get all available expirations and strikes
   - Calculate implied volatility metrics

2. **Run Options Kill Screens** (from `schema/options_kill_screens.json`):
   - Options existence check
   - Open interest ≥ thresholds (100 for target, 50 for adjacent)
   - Average volume ≥ thresholds (20 for strike, 100 total)
   - Bid-ask spread < 10% of mid
   - Time to expiration: Find expiration matching catalyst + buffer
   - IV sanity checks (10%-300%)
   - Archetype-specific checks (LEAPS for activist, deal price strike for merger arb)

3. **Breakeven Analysis**
   - If options screens pass, calculate:
     - Stock move needed for breakeven: `(strike + premium - current_price) / current_price`
     - Effective leverage: `notional_exposure / premium_paid`
     - Premium as % of notional: `premium / (shares * stock_price)`
   - Compare to mispricing gap from thesis
   - If stock_move_needed < mispricing_gap AND leverage > 3x → Options favorable

4. **Generate Options Recommendation**
   - **Options viable + favorable:** "Recommend options - better risk/reward than equity"
   - **Options viable but marginal:** "Options available - analyze will present both approaches"
   - **Options not viable:** "Options screened out - use equity (reason: low liquidity / wide spreads / no suitable expiration)"
   - **Archetype doesn't support:** "Equity only for this archetype"

**Add to watchlist file in Step 3 below:**
```markdown
## Options Analysis
**Viable:** Yes/No
**Reason:** [Why options passed/failed screens]
**Recommended Strike:** $X (ATM/OTM)
**Recommended Expiration:** YYYY-MM-DD (67 DTE)
**Breakeven Stock Move:** +15% (vs +25% mispricing gap → favorable)
**Effective Leverage:** 4.2x
**Recommendation:** Consider options - premium $X for Y contracts
```

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
- [x] Market cap: {value} (< threshold)
- [x] Archetype-specific: {list archetype kill screens}

**v1.1 Archetype-Specific Data:**
- **PDUFA**: Form 483 with OAI: {Yes/No}, EMA approved: {Yes/No}
- **Insider**: Opportunistic insiders: {count}, Routine insiders: {count}
- **Activist/Spin-off**: WARN filing: {Yes/No}
- **Merger Arb**: Note any second request, CFIUS, or China exposure

## Options Analysis
**Archetype Supports Options:** {Yes/No}
**Options Viable:** {Yes/No}
**Options Screening:**
- Open Interest: {value} (threshold: 100) → {PASS/FAIL}
- Bid-Ask Spread: {X}% (threshold: 10%) → {PASS/FAIL}
- Suitable Expiration: {YYYY-MM-DD} ({X} DTE) → {PASS/FAIL}
- IV: {X}% (percentile: {Y}) → {PASS/FAIL}

**If Options Viable:**
- **Recommended Strategy:** {long_calls / call_debit_spread / leaps_calls}
- **Strike:** ${X} ({ATM/OTM description})
- **Expiration:** {YYYY-MM-DD} ({X} DTE)
- **Estimated Premium:** ${X} per contract
- **Position Size:** {Y} contracts (${Z} total premium at {A}% of portfolio)
- **Breakeven Stock Price:** ${X} (+{Y}% from current)
- **Effective Leverage:** {Z}x
- **Comparison to Mispricing:** Breakeven {Y}% vs expected move {Z}% → {Favorable/Unfavorable}

**Recommendation:** {Options preferred / Equity preferred / Consider both}
**Reason:** {Brief explanation}

**If Options Not Viable:**
- **Reason:** {Low liquidity / Wide spreads / No suitable expiration / Archetype doesn't support}
- **Fallback:** Use equity approach

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

### Step 5: Write Log Entry

Append to `logs/analyze/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T14:30:00Z",
  "skill": "analyze",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "outcome": "PASS",
  "metrics": {
    "m_score": -2.1,
    "z_score": 2.5,
    "market_cap": 4500000000,
    "kill_screens_passed": true
  },
  "data_sources": ["IBKR", "SEC API"],
  "execution_time_ms": 2150,
  "notes": "All kill screens passed. Watchlist file created."
}
```

Log all executions for pattern analysis and debugging.

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
