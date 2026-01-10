# Technical Specification: Idiosyncratic Trading System
## Version 1.0 | 2025-01-05

---

## 1. System Overview

### 1.1 Architecture Philosophy
This is an **agentic trading system** where Claude Code skills autonomously execute a catalyst-driven special situations framework. The system balances **automation with human oversight**, learning from decisions over time while maintaining user control over critical choices.

**Core Principles:**
- **Ask-first over fail-safe**: When uncertain, agents interrupt for clarification rather than defaulting conservatively
- **Fresh evaluation over consistency**: Always re-score with current data, but track why decisions changed
- **Cross-checking over trust**: Validate data across multiple sources before using
- **Graduated responses**: Use thresholds and confidence levels rather than binary decisions

### 1.2 Agent Autonomy Model

**Agents should:**
- ✅ Try alternative data sources before failing
- ✅ Provide context and precedents when asking questions
- ✅ Auto-execute low-stakes decisions (e.g., 8.2 score → CONDITIONAL)
- ✅ Cross-check suspicious data automatically
- ✅ Suggest next steps after completing tasks

**Agents should NOT:**
- ❌ Auto-fail without trying alternatives
- ❌ Ask obvious questions
- ❌ Auto-execute high-stakes decisions (kill screen overrides, exits)
- ❌ Accept anomalous data without validation
- ❌ Run scheduled tasks (not yet supported)

**Interruption Thresholds:**
- **Always ask:** Kill screen violations (if agent confidence low), exit signals at exact threshold (weighted_sum = 2.0), cockroach ambiguity
- **Auto-decide:** Scoring edge cases (8.2 → CONDITIONAL), data source fallbacks, borderline metrics (strict but not extreme)
- **Suggest:** Next skill in workflow, position adjustments on regime change, re-scoring when material news detected

---

## 2. Data Management

### 2.1 Data Source Strategy

#### Price Data (Real-time Requirements)
**Strategy:** Parallel fetch with graceful degradation
```
1. Try IBKR paper account (real-time)
2. If fails → Stooq (delayed 15min)
3. If fails → Yahoo Finance
4. If all fail → Log error, notify user, halt operation
```

**Philosophy:** Not day trading, so delayed data acceptable for screening. Real-time preferred for active position monitoring but not critical.

**Caching:**
- Daily cache for non-critical operations
- Refresh on explicit skill re-run
- No automatic scheduled refreshes (not yet supported)

#### Financial Data (Kill Screens)
**Strategy:** Fresh fetch with smart caching
```
1. Always re-fetch when `screen` skill runs (fresh data priority)
2. Cache for session duration (same ticker screened multiple times = use cache)
3. Invalidate cache if:
   - Filing date passed (check SEC API for new 10-Q/10-K)
   - User explicitly requests refresh
   - Restatement detected
```

**Calculation Source Priority:**
1. Pre-calculated (SEC API aggregated data)
2. Manual calculation from raw financials
3. Third-party screening tools (fallback)

#### Event Data (Catalysts)
**Sources:**
- PDUFA dates: `accessdata.fda.gov/scripts/cder/daf/`
- Activist 13Ds: `sec.gov/cgi-bin/browse-edgar` (daily check future)
- Merger announcements: Web search, SEC 8-K filings
- Legislative: Manual entry (tracking bills/regulations)

**Update Frequency:**
- Current: Manual invocation of `scan` skill
- Future: Weekly scheduled scan (Monday mornings)

### 2.2 Data Validation & Sanity Checks

#### Anomaly Detection Rules

**M-Score (expected range: -2 to +2):**
```
IF m_score > 10 OR m_score < -10:
    auto_reject()
    try_alternative_source()
    flag_suspicious("M-Score {value} outside expected range -2 to +2")
```

**Price Data:**
```
IF price < $0.10 OR price_change > 50% in 1 day:
    cross_check_sources([IBKR, Stooq, Yahoo])
    IF all_sources_agree:
        accept_data()
    ELSE:
        alert("Price anomaly detected. Cross-check failed.")
        use_previous_day_price()
```

**Z-Score (expected range: -5 to +10):**
```
IF z_score borderline (e.g., 1.79 vs threshold 1.81):
    strict_enforcement()  # 1.79 < 1.81 = FAIL
    # No tolerance band (not that strict, but clear rules)
```

#### Cross-Checking Protocol
**Always cross-check:**
- Price anomalies (>50% moves, <$0.10 prices)
- Outlier financial metrics (M-Score >10, Z-Score <-10)
- Conflicting data between sources (>5% difference)

**Single source acceptable:**
- Normal-range metrics
- Consistent with historical data
- Matches expectations for company/industry

---

## 3. Archetype & Classification Logic

### 3.1 Hybrid Archetype Handling

**When multiple archetypes apply** (e.g., Activist + Spin-off):

```python
def determine_primary_archetype(signals):
    """
    Use archetype with higher score/confidence, note secondary signal.
    """
    scored_archetypes = []

    if activist_13d_filed and spin_off_announced:
        activist_score = calculate_activist_confidence()
        spinoff_score = calculate_spinoff_confidence()

        if activist_score > spinoff_score:
            primary = "activist"
            secondary = "spinoff"
            # Use activist rules: 6% max, enter on 13D, use activist scoring adjustments
        else:
            primary = "spinoff"
            secondary = "activist"
            # Use spinoff rules: 8% max, enter day 30-60, use spinoff info parity weights

    return {
        "primary_archetype": primary,
        "secondary_signals": [secondary],
        "rationale": "Activist initiated, but spin-off is primary catalyst",
        "scoring_note": "Secondary activist signal adds confidence but not score adjustment"
    }
```

**Trade JSON structure for hybrids:**
```json
{
  "archetype": "spinoff",
  "secondary_signals": ["activist"],
  "archetype_determination": {
    "rationale": "Spin-off timing is entry catalyst, activist pushed for it",
    "confidence": 0.85,
    "alternative_archetype_considered": "activist"
  }
}
```

---

## 4. Kill Screens & Scoring

### 4.1 Kill Screen Edge Cases

#### Data Unavailability Handling
```
IF sec_api_down:
    try_alternative_sources([yahoo_finance, web_scraping, cached_data])

    IF all_sources_fail:
        log_error("All data sources failed for {ticker}")
        notify_user("Cannot screen {ticker} - data unavailable. Manual review needed.")
        status = "data_unavailable"
        # Do NOT auto-PASS - flag for human review
```

#### Restatements
```
IF restatement_detected(ticker):
    calculate_m_score_both_versions()

    ask_user(f"""
    {ticker} has restated financials:
    - Original M-Score: {original} (PASS)
    - Restated M-Score: {restated} (FAIL)

    Which to use?
    A) Restated (most accurate)
    B) Original (what market saw at time)
    C) PASS (conservative approach)
    """)
```

#### Industry-Adjusted Z-Score
```python
def get_z_score_threshold(ticker):
    industry = get_industry(ticker)

    thresholds = {
        "telecom_media": 1.5,
        "biotech_pharma": 1.5,
        "software_saas": 2.0,
        "utilities": 2.5,
        "default": 1.81
    }

    threshold = thresholds.get(industry, 1.81)

    # Require validation metrics for adjusted thresholds
    if industry != "default":
        validation = check_validation_metrics(ticker, industry)
        return threshold, validation

    return threshold, None
```

### 4.2 Scoring Consistency & Drift Tracking

**Always re-score fresh**, but track why it changed:

```json
{
  "scoring_history": [
    {
      "date": "2025-01-02",
      "score": 8.5,
      "catalyst": 2.0,
      "mispricing": 1.5,
      "noise_survival": 1.5,
      "context": "Initial analysis, 18mo cash runway"
    },
    {
      "date": "2025-02-01",
      "score": 9.2,
      "catalyst": 2.0,
      "mispricing": 2.0,
      "noise_survival": 1.5,
      "context": "Competitor CRL increased approval odds",
      "changes": {
        "mispricing": "+0.5 (market hasn't priced in competitor failure)"
      }
    }
  ],
  "drift_analysis": {
    "total_change": "+0.7",
    "factors_changed": ["mispricing"],
    "thesis_impact": "strengthened"
  }
}
```

**Scoring edge cases:**
- Score 8.2 (just below 8.25 BUY threshold): **Auto-CONDITIONAL**
- Score 8.25 exactly: **BUY** (meets threshold)
- Score varies between sessions for same ticker: **Track in scoring_history**, note context

---

## 5. Precedent Learning System

### 5.1 Context-Aware Precedent Matching

**Only suggest precedents when factors match:**

```python
def find_relevant_precedents(current_idea):
    """
    Precedents must match on key dimensions, not just archetype.
    """
    filters = {
        "archetype": current_idea.archetype,
        "similar_catalyst": True,  # PDUFA approval pathway, activist tier, etc.
    }

    # Archetype-specific matching
    if archetype == "pdufa":
        filters.update({
            "therapeutic_area": current_idea.therapeutic_area,
            "approval_pathway": current_idea.pathway,  # BLA vs NDA
            "trial_design": current_idea.trial_type    # Pivotal vs Phase 3
        })

    if archetype == "activist":
        filters.update({
            "activist_tier": current_idea.activist_tier,
            "industry": current_idea.industry,
            "campaign_type": current_idea.type  # Proxy fight vs board seats vs M&A push
        })

    matches = search_precedents(filters)

    # Rank by similarity score
    return rank_by_relevance(matches, current_idea)
```

**Precedent confidence scoring:**
```
After 1 similar case:  "tentative pattern" (suggest but note limited data)
After 3-5 cases:       "established pattern" (higher confidence suggestion)
After 10+ cases:       "framework rule candidate" (suggest schema promotion)
```

**Note:** Don't over-complicate initially. Start simple, add complexity as patterns emerge.

---

## 6. Position Sizing & Risk Management

### 6.1 Position Size Hierarchy

**When constraints conflict:**
```
Priority: Kellner Rule > Archetype Cap > Kelly Optimization

Example:
  Kelly suggests:     $1,200
  Archetype cap:      $750 (3% of $25K)
  Kellner max loss:   $500 (2% of $25K)

  Stop distance: 20% below entry
  Kellner-adjusted position: $2,500 (20% loss = $500)

  Final position: min($2,500, $750) = $750
  Binding constraint: Archetype cap
```

**Log which constraint was binding:**
```json
{
  "position_sizing": {
    "kelly_suggested": 1200,
    "archetype_cap": 750,
    "kellner_adjusted": 2500,
    "final_position": 750,
    "binding_constraint": "archetype_cap",
    "rationale": "Kelly suggested $1,200 but Merger Arb capped at 3% ($750)"
  }
}
```

### 6.2 Archetype-Specific Stop Logic

**Vary stop loss by archetype** (if easy and clear to implement):

```python
def calculate_stop_loss(archetype, entry_price, position_value, account_size):
    kellner_max_loss = account_size * 0.02  # $500 for $25K account

    if archetype == "merger_arb":
        # Use deal spread as natural stop
        stop = deal_price - (deal_spread * 0.5)  # Exit if spread widens 50%
        return stop

    elif archetype == "pdufa":
        # Binary event - no meaningful stop
        # Already sized smaller (1.5% vs 3%)
        return None  # No technical stop

    elif archetype == "spinoff":
        # Technical stop: 200-day MA
        ma_200 = get_200_day_ma(ticker)
        stop = ma_200 * 0.98  # 2% below MA
        return stop

    elif archetype == "activist":
        # Time-based stop: if no progress in 6 months
        time_stop = entry_date + timedelta(days=180)
        return time_stop

    else:
        # Default: 2% portfolio loss
        stop_distance = kellner_max_loss / (position_value / entry_price)
        return entry_price - stop_distance
```

**Stop enforcement:**
- **Alert, don't auto-exit:** "TRD-2025-001 hit stop price $95.00. Exit?"
- **Only auto-exit for:** Cockroach Rule, Thesis Break (hard exits)
- **Manual review for:** Technical stops, time-based stops

---

## 7. Info Parity & Exit Logic

### 7.1 Time-Aware Media Triggers

**Media coverage timing varies by archetype:**

```python
def check_media_trigger(ticker, archetype, catalyst_date):
    """
    Time-aware media trigger to avoid false positives.
    """
    articles = search_mainstream_media(ticker, days=7)

    if archetype == "pdufa":
        # Ignore pre-catalyst speculation articles
        days_to_catalyst = (catalyst_date - today).days

        if days_to_catalyst <= 1:
            # "FDA decision tomorrow" articles are noise, not info parity
            articles = filter_articles(articles, exclude_speculative=True)

    elif archetype == "merger_arb":
        # Post-announcement coverage is normal, not info parity
        # Only trigger on NEW information (e.g., DOJ investigation)
        articles = filter_articles(articles, only_material_developments=True)

    elif archetype == "activist":
        # 13D filing coverage expected
        # Trigger on OUTCOME coverage (board seats, CEO change)
        articles = filter_articles(articles, outcome_only=True)

    mainstream_count = len([a for a in articles if a.source in MAINSTREAM_OUTLETS])

    return mainstream_count >= 2
```

**Mainstream outlets definition:**
```python
MAINSTREAM_OUTLETS = [
    "Wall Street Journal", "Bloomberg", "Financial Times",
    "CNBC", "Reuters", "New York Times Business"
]
```

### 7.2 Graduated Exit Thresholds

**Dynamic thresholds based on archetype and position state:**

```python
def get_exit_thresholds(archetype, position_state):
    """
    Exit thresholds vary by archetype and whether position partially exited.
    """
    base_thresholds = {
        "pdufa": {
            "50_pct": 1.8,  # Exit faster for binary events
            "full": 2.5     # After 50% exit, lower full threshold
        },
        "spinoff": {
            "25_pct": 1.5,
            "50_pct": 2.0,
            "75_pct": 2.5,
            "full": 3.0
        },
        "default": {
            "50_pct": 2.0,
            "full": 3.0
        }
    }

    thresholds = base_thresholds.get(archetype, base_thresholds["default"])

    # Adjust if position partially exited
    if position_state.percent_exited > 0:
        # Lower full exit threshold after partial exit
        if "full" in thresholds:
            thresholds["full"] = max(thresholds["full"] - 0.5, 2.0)

    return thresholds
```

**Implementation preference:**
- **If easy:** Archetype-specific thresholds (PDUFA exits faster)
- **If complex:** Use graduated exits (25% at 1.5, 50% at 2.0, 75% at 2.5, 100% at 3.0)

**Exit signal at exact threshold (weighted_sum = 2.0):**
- **Ask user:** "TRD-2025-001 info parity exactly 2.0. Exit 50%?"

---

## 8. Multi-Catalyst Sequencing

### 8.1 Milestone Tracking

**Track as ONE trade with evolving catalysts** (if easy and clear):

```json
{
  "trade_id": "TRD-2025-003",
  "ticker": "SRPT",
  "archetype": "pdufa",
  "status": "active",

  "milestones": [
    {
      "milestone": "NDA accepted",
      "date": "2024-12-01",
      "status": "completed",
      "impact": "De-risking event",
      "score_before": 7.8,
      "score_after": 8.2,
      "action_taken": "none"
    },
    {
      "milestone": "AdCom meeting",
      "date": "2025-01-15",
      "status": "completed",
      "outcome": "positive (10-2 vote)",
      "impact": "Thesis strengthened",
      "score_before": 8.2,
      "score_after": 9.1,
      "action_taken": "Updated target price from $180 to $220"
    },
    {
      "milestone": "PDUFA date",
      "date": "2025-02-15",
      "status": "pending",
      "impact": "Final catalyst",
      "score_current": 9.1,
      "confidence": 0.95,
      "planned_action": "Full exit on outcome"
    }
  ],

  "position_scaling": {
    "initial_entry": {
      "date": "2024-12-05",
      "shares": 20,
      "rationale": "Post-NDA acceptance, reduced size for AdCom risk"
    },
    "scale_up": {
      "date": "2025-01-16",
      "shares_added": 10,
      "total_shares": 30,
      "rationale": "Positive AdCom increases confidence"
    }
  }
}
```

**Re-scoring triggers:**
- Major milestones reached
- Material new information emerges
- User invokes `score` skill explicitly

**Position adjustment suggestions:**
- Thesis strengthens (score 9.2): "Consider scaling up within archetype cap?"
- Thesis weakens (score 7.0): "Score dropped below BUY threshold. Treat as soft thesis break - exit 50%?"

---

## 9. Portfolio-Level Management

### 9.1 Correlation Detection

**New skill: Portfolio-level correlation analysis**

```python
def check_portfolio_correlation():
    """
    Analyze active trades for correlated risks.
    """
    active_trades = load_active_trades()

    # Sector correlation
    sector_exposure = group_by(active_trades, "sector")
    for sector, trades in sector_exposure.items():
        if len(trades) >= 3:
            alert(f"""
            Portfolio concentration alert:
            - {len(trades)} active trades in {sector}
            - Combined exposure: {sum(t.position_pct)}%
            - Macro risks: {identify_macro_risks(sector)}

            Recommendation: Diversify or reduce sector exposure
            """)

    # Macro sensitivity correlation
    rate_sensitive = [t for t in active_trades if t.rate_sensitive]
    if len(rate_sensitive) >= 3:
        alert(f"""
        Rate sensitivity correlation detected:
        - {len(rate_sensitive)} trades exposed to rate changes
        - Tickers: {[t.ticker for t in rate_sensitive]}

        Monitor Fed policy and adjust if rates spike
        """)

    # Archetype concentration
    archetype_exposure = group_by(active_trades, "archetype")
    for archetype, trades in archetype_exposure.items():
        total_exposure = sum(t.position_pct for t in trades)
        cap = get_archetype_aggregate_cap(archetype)

        if total_exposure > cap:
            alert(f"""
            Archetype concentration exceeded:
            - {archetype}: {total_exposure}% (cap: {cap}%)
            - Trades: {[t.ticker for t in trades]}

            Action: Reduce position sizes or close marginal trades
            """)
```

### 9.2 Regime-Based Position Management

**When regime changes (VIX spike to 32):**

```python
def handle_regime_change(new_regime):
    """
    Suggest position adjustments on regime changes.
    """
    if new_regime.vix > 30:
        # Sustained crisis regime
        merger_arb_trades = [t for t in active_trades if t.archetype == "merger_arb"]

        suggest(f"""
        Regime Change: VIX {new_regime.vix} (sustained crisis)

        Active Merger Arb positions:
        - {trade1.ticker}: 3.0% exposure
        - {trade2.ticker}: 2.5% exposure

        Recommendation: Consider reducing merger arb exposure by 50%

        Actions:
        1. Exit 50% of {trade1.ticker}
        2. Exit 50% of {trade2.ticker}
        3. Pause new merger arb positions until VIX < 25
        """)

    elif new_regime.hy_oas_widened_100bp:
        # Credit stress
        suggest(f"""
        Credit Condition: HY OAS widened {new_regime.oas_change}bp

        Impact on Merger Arb: Deal financing may become stressed

        Recommendation: Review all active merger arb trades for financing risk
        """)
```

**Monitoring frequency adjustment:**
- Normal: Daily
- Elevated (VIX 20-30): Daily + intraday check after major moves
- Crisis (VIX >30): Consider twice daily (not auto-scheduled, user invokes)

---

## 10. Order Execution & Trade Management

### 10.1 Entry Order Logic

**Default: Limit orders at bid/ask midpoint**

```python
def place_entry_order(ticker, shares, entry_price):
    """
    Default to limit order with optional premium for fill probability.
    """
    bid, ask = get_quotes(ticker)
    midpoint = (bid + ask) / 2

    # Option 1: Midpoint (better price, risk no fill)
    limit_price = midpoint

    # Option 2: Slight premium (ensure fill)
    # limit_price = bid + 0.05  # For buys

    order = {
        "ticker": ticker,
        "action": "BUY",
        "shares": shares,
        "order_type": "LMT",
        "limit_price": limit_price,
        "time_in_force": "DAY"
    }

    # Execute via IBKR
    result = ibkr_api.place_order(order)

    # Verify fill
    if not result.filled:
        retry_entry_order(order)

    return result

def retry_entry_order(original_order):
    """
    If limit order doesn't fill, retry with adjusted price.
    """
    wait(minutes=30)

    # Check if still want to enter
    current_price = get_price(original_order.ticker)

    if current_price > original_order.limit_price * 1.05:
        # Price moved away >5%
        cancel_order(original_order)
        notify("Entry order not filled. Price moved {current_price}. Mark as missed entry?")
    else:
        # Adjust limit to current midpoint
        bid, ask = get_quotes(original_order.ticker)
        new_limit = (bid + ask) / 2

        adjusted_order = original_order.copy()
        adjusted_order.limit_price = new_limit

        ibkr_api.place_order(adjusted_order)
```

### 10.2 Exit Order Logic

**Always market orders for exits:**

```python
def place_exit_order(trade_id, exit_percent):
    """
    Exit signals require immediate execution - use market orders.
    """
    trade = load_trade(trade_id)

    shares_to_exit = trade.shares * (exit_percent / 100)

    order = {
        "ticker": trade.ticker,
        "action": "SELL",
        "shares": shares_to_exit,
        "order_type": "MKT",
        "time_in_force": "IOC"  # Immediate or cancel
    }

    result = ibkr_api.place_order(order)

    # Log exit
    log_exit(trade_id, exit_percent, result.fill_price, result.timestamp)

    # Update trade JSON
    update_trade_position(trade_id, shares_to_exit, result.fill_price)

    return result
```

---

## 11. Error Handling & Recovery

### 11.1 Data Source Failures

**Retry with alternative sources:**

```python
def fetch_price_with_fallback(ticker):
    """
    Parallel fetch: try IBKR first, fallback to Stooq.
    """
    sources = [
        ("IBKR", lambda: ibkr_api.get_price(ticker)),
        ("Stooq", lambda: stooq_api.get_price(ticker)),
        ("Yahoo", lambda: yahoo_api.get_price(ticker))
    ]

    for source_name, fetch_func in sources:
        try:
            price = fetch_func()
            if validate_price(price):
                log(f"Price for {ticker}: ${price} (source: {source_name})")
                return price
        except Exception as e:
            log(f"{source_name} failed for {ticker}: {e}")
            continue

    # All sources failed
    notify(f"All price sources failed for {ticker}. Manual review needed.")
    raise DataUnavailableError(f"Cannot get price for {ticker}")
```

### 11.2 Partial Failures

**Complete successful operations, alert about failures:**

```python
def monitor_all_trades():
    """
    Monitor all active trades. If one fails, continue with others.
    """
    active_trades = load_active_trades()

    successful = []
    failed = []

    for trade in active_trades:
        try:
            result = monitor_single_trade(trade)
            successful.append(result)
        except Exception as e:
            log(f"Monitor failed for {trade.ticker}: {e}")
            failed.append({
                "trade_id": trade.trade_id,
                "ticker": trade.ticker,
                "error": str(e)
            })

    # Report results
    summary = f"""
    Monitoring complete:
    - Successful: {len(successful)}/{len(active_trades)}
    - Failed: {len(failed)}
    """

    if failed:
        alert(f"""
        {summary}

        Failed trades:
        {format_failures(failed)}

        Action required: Manually check these positions
        """)
    else:
        log(summary)

    return {"successful": successful, "failed": failed}
```

---

## 12. Logging & Audit Trail

### 12.1 Log Structure

**Standard logging: Outcome + key metrics**

```
Per-skill logs with dates for easy navigation:
- logs/screen/2025-01-05.log
- logs/analyze/2025-01-05.log
- logs/score/2025-01-05.log
- logs/monitor/2025-01-05.log
- logs/open/2025-01-05.log
- logs/close/2025-01-05.log
```

**Log entry format:**
```json
{
  "timestamp": "2025-01-05T09:30:00Z",
  "skill": "screen",
  "ticker": "SRPT",
  "outcome": "PASS",
  "metrics": {
    "m_score": -2.1,
    "z_score": 2.5,
    "market_cap": 4500000000
  },
  "data_sources": ["SEC API", "Yahoo Finance"],
  "execution_time_ms": 1250,
  "notes": "All kill screens passed"
}
```

### 12.2 Decision Paper Trail

**For PASS decisions, log:**
- Data sources used
- Kill screen values
- Why it failed
- Alternative sources checked (if insightful)

**Don't log:**
- Hypothetical "what if different thresholds" scenarios

**Example PASS log:**
```json
{
  "date": "2025-01-05",
  "ticker": "AQST",
  "archetype": "pdufa",
  "decision": "PASS",
  "reason": "Failed kill screens",
  "failed_screens": ["altman_z_score", "pdufa_cash_runway"],
  "metrics": {
    "z_score": -5.39,
    "threshold": 1.5,
    "cash_runway_months": 4.9,
    "threshold_months": 18
  },
  "data_sources": {
    "financials": "SEC 10-Q (2024-Q3)",
    "price": "Yahoo Finance",
    "backup_checked": ["Stooq (confirmed Z-Score calculation)"]
  },
  "lessons": "Biotech with <6 month runway is automatic fail even if drug promising"
}
```

---

## 13. Performance Tracking & Metrics

### 13.1 Review Skill Output

**Focus: Trade performance + decision quality**

```markdown
# Weekly Review: 2025-01-05 to 2025-01-11

## Trade Performance
- Active trades: 3
- Closed this week: 1
- Win rate (all-time): 68% (17W / 8L)
- Average return: +12.3%
- Sharpe ratio: 1.6

## Closed This Week
### TRD-2025-002 (WIN)
- Ticker: DVAX
- Archetype: PDUFA
- Entry: $8.50 (2025-01-03)
- Exit: $12.20 (2025-01-10)
- Return: +43.5%
- Exit trigger: Full approval announced
- Score at entry: 8.7

## Decision Quality
### BUY Signals (≥8.25)
- Opened: 2
- Win rate: 100% (1W / 0L, 1 still open)
- Average return: +43.5%

### PASS Decisions (Kill Screens)
- Declined: 4
- Hindsight analysis:
  - AQST: PASS (Z-Score -5.39) → Stock -12% since (correct decision)
  - MKTX: PASS (Market cap $50.2B) → Stock +3% since (marginal miss)
  - BHVN: PASS (M-Score -1.5) → Stock -8% since (correct decision)

## Active Positions
1. TRD-2025-001 (SRPT): Up 8%, on track for PDUFA date
2. TRD-2025-003 (ABBV): Up 2%, activist campaign progressing
3. TRD-2025-004 (TRUP): Down 3%, spin-off day 45

## Alerts
- None this week

## Framework Calibration
- BUY threshold (8.25): Still producing 68% win rate ✅
- PDUFA archetype: 2-0 this month, consider increasing allocation
- Activist archetype: No new opportunities, need better sourcing
```

**Metrics priority:**
1. Win rate (%)
2. Sharpe ratio
3. BUY signal accuracy
4. PASS decision hindsight validation

**Simplification note:** Keep report concise. Too much detail not useful for user and AI without infinite context.

---

## 14. Alerting & Notifications

### 14.1 Alert Priority Levels

**Immediate alerts (must act now):**
- Exit signal triggered (weighted_sum ≥ 2.0)
- Cockroach observed
- Stop loss hit
- Regime change (VIX crossed threshold)

**Daily digest (check once per day):**
- Monitoring updates (no action needed)
- Position P&L summaries

**Weekly review (check end of week):**
- Framework calibration suggestions
- Performance metrics

### 14.2 Alert Persistence

**Method:** Write to `alerts.json` + console output (if easy)

```json
{
  "alerts": [
    {
      "id": "ALERT-2025-001",
      "timestamp": "2025-01-05T14:30:00Z",
      "priority": "immediate",
      "type": "exit_signal",
      "trade_id": "TRD-2025-001",
      "ticker": "SRPT",
      "message": "Info parity weighted sum = 2.1. Exit 50% recommended.",
      "action_required": true,
      "acknowledged": false
    },
    {
      "id": "ALERT-2025-002",
      "timestamp": "2025-01-05T09:00:00Z",
      "priority": "immediate",
      "type": "regime_change",
      "message": "VIX crossed 30 threshold (current: 32). Review merger arb positions.",
      "action_required": true,
      "acknowledged": false
    }
  ]
}
```

**Alert acknowledgment:**
- User acknowledges via skill or command
- Acknowledged alerts archived to `alerts_archive.json`

**No external alerts:** No email, Slack, or push notifications. CLI + alerts.json only.

---

## 15. Trade Lifecycle & File Management

### 15.1 Trade ID Format

**More info in filename is OK:**

```
Format: TRD-{YYYY}{MM}{DD}-{TICKER}-{ARCHETYPE}

Examples:
- TRD-20250105-SRPT-PDUFA
- TRD-20250110-ABBV-ACTIVIST
- TRD-20250115-TRUP-SPINOFF
```

**Benefits:**
- Readable without opening file
- Sortable by date
- Grep-friendly

### 15.2 File Organization

**Closed trades: Organize by outcome**

```
trades/
├── active/
│   ├── TRD-20250105-SRPT-PDUFA.json
│   └── TRD-20250110-ABBV-ACTIVIST.json
├── closed/
│   ├── wins/
│   │   ├── TRD-20250103-DVAX-PDUFA.md
│   │   └── TRD-20241220-XYZ-MERGER.md
│   └── losses/
│       └── TRD-20241215-ABC-ACTIVIST.md
├── conditional/
│   └── TRD-20250102-MKTX-LEGISLATIVE.json  # Score 7.2, user declined
└── passed/
    └── 2025-01-05-AQST-PDUFA.json  # Failed kill screens
```

**Alternative:** Organize by archetype
```
trades/closed/
├── pdufa/
├── merger_arb/
├── activist/
├── spinoff/
└── ...
```

**Preference:** Outcome-based (wins/losses) is better for learning from what worked vs. didn't.

### 15.3 Event Archiving

**Auto-archive past catalysts:**

```python
def archive_past_events():
    """
    Move completed events to archive.
    """
    events = load_events("universe/events.json")

    active_events = []
    archived_events = []

    for event in events:
        if event.catalyst_date < today:
            event.status = "completed"
            archived_events.append(event)
        else:
            active_events.append(event)

    # Write back
    save_events("universe/events.json", active_events)
    append_events("universe/events_archive.json", archived_events)
```

---

## 16. Schema Evolution & Versioning

### 16.1 Version Control

**Schema versioning:**
```
Current: v3.7 (pre-release, will reset to v1.0 at launch)
Future: v1.0, v1.1, v2.0, etc.
```

**Version format in CONFIG.json:**
```json
{
  "framework_version": "1.0",
  "schema_format_version": "1.0"
}
```

**Schema CHANGELOG:**
```markdown
# Schema Changelog

## v3.7 (2025-01-05)
### Added
- Market cap ceiling kill screen ($50B base, $100B merger arb)
- PDUFA financial health screens (cash runway, D/E, net cash)
- Industry-adjusted Z-Score thresholds

### Changed
- PDUFA max position reduced from 2% to 1.5%
- Legislative max position increased from 1.5% to 2%

### Deprecated
- (None)
```

### 16.2 Schema Migration

**Handling old trades when schema changes:**

```python
def handle_schema_update(new_version):
    """
    When schema updates, track version per trade but don't force re-scoring.
    """
    active_trades = load_active_trades()

    for trade in active_trades:
        if trade.framework_version != new_version:
            # Add migration note
            trade.metadata["schema_migration"] = {
                "original_version": trade.framework_version,
                "current_version": new_version,
                "note": "Trade scored under v3.6 rules, grandfathered in"
            }

            # Flag if wouldn't qualify under new rules
            new_score = re_score_with_new_rules(trade, new_version)
            if new_score < BUY_THRESHOLD:
                flag_trade(trade, f"""
                Note: Under current framework (v{new_version}),
                this trade would score {new_score} (below threshold).

                Original score (v{trade.framework_version}): {trade.score}

                No action required, but monitor closely.
                """)
```

**Schema update process:**
1. User updates `schema/*.json` files
2. Increment `framework_version` in `CONFIG.json`
3. Document changes in `schema/CHANGELOG.md`
4. System flags active trades that wouldn't qualify under new rules (but doesn't force close)

---

## 17. Post-Mortem & Learning

### 17.1 Post-Mortem Depth

**Auto-generate post-mortem with:**
- Basic metrics (entry/exit prices, return %, duration)
- Exit trigger (what caused exit)
- Link to similar precedents
- Scoring drift analysis

```markdown
# Post-Mortem: TRD-20250103-DVAX-PDUFA

## Overview
- **Ticker:** DVAX
- **Archetype:** PDUFA
- **Entry Date:** 2025-01-03
- **Exit Date:** 2025-01-10
- **Duration:** 7 days
- **Entry Price:** $8.50
- **Exit Price:** $12.20
- **Return:** +43.5%
- **Outcome:** WIN

## Entry Thesis
FDA AdCom positive (10-2 vote), strong efficacy data, clean safety profile.
Approval highly likely (95% confidence).

## Exit Trigger
- **Type:** Catalyst occurred (full approval)
- **Info Parity:** 3.2 (media coverage + IV spike)
- **Action:** Full exit

## Scoring Analysis
### Entry Score: 8.7
- Catalyst: 2.0 (PDUFA date known, AdCom positive)
- Mispricing: 2.0 (Market at $8.50, fair value $13)
- Noise Survival: 2.0 (18mo cash runway, strong balance sheet)
- Downside Floor: 1.5 (Asset value ~$6, limited downside)
- Risk/Reward: 2.0 (3.5:1 ratio)
- Info Half-Life: 0.2 (AdCom widely covered, edge limited)

### Scoring Drift
No drift - thesis played out as expected.


**Pattern:** Post-positive-AdCom PDUFA trades = 92% win rate (11/12)

## Lessons Learned
1. ✅ Positive AdCom is strong signal - continue prioritizing
2. ✅ Info half-life was low (0.2) but still profitable due to catalyst clarity
3. ⚠️ Entry could have been earlier (day after AdCom vs 3 days later)
4. 💡 Consider partial exit at 50% gain to lock in profits (reached +47% intraday)

## What Would Have Changed Score
- If scored retrospectively: 9.0 (increase mispricing to 2.5, given actual approval)
- Entry thesis was slightly conservative on downside floor (actual floor ~$7)

## Framework Feedback
**Pattern observed:** Post-positive-AdCom PDUFAs (n=12) show 92% approval rate.
**Recommendation:** Consider adding "+0.5 adjustment for positive AdCom" to schema.
```

---

## 18. Skill Coordination & Workflows

### 18.1 Current State (Manual)

**Current workflow:**
```
User: /analyze SRPT
Agent: [Runs kill screens, creates watchlist]
Agent: "Kill screens passed. Suggest next step: score SRPT"

User: /score SRPT
Agent: [Calculates 6-filter score]
Agent: "Score 8.7 (BUY). Suggest next step: open SRPT"

User: /open SRPT
Agent: [Calculates position size, creates trade]
```

**Skill suggestions at end of execution:**
```python
def suggest_next_step(current_skill, result):
    """
    After completing a skill, suggest logical next step.
    """
    suggestions = {
        "screen": {
            "passed": "Kill screens passed. Run 'analyze {ticker}' for full framework analysis.",
            "failed": "Kill screens failed. Idea declined. Run 'scan' to find new opportunities."
        },
        "analyze": {
            "passed": "Watchlist created. Run 'score {ticker}' to complete 6-filter scoring.",
            "failed": "Kill screens failed. Logged to passed/. Run 'scan' for new ideas."
        },
        "score": {
            "buy": "Score {score} ≥ 8.25 (BUY). Run 'open {ticker}' to create position.",
            "conditional": "Score {score} is CONDITIONAL (6.5-8.24). Review and decide if opening.",
            "pass": "Score {score} < 6.5 (PASS). Idea declined. Logged to passed/."
        },
        "open": {
            "success": "Position opened. Run 'monitor' daily to track exit signals."
        },
        "monitor": {
            "no_alerts": "All positions stable. Re-run 'monitor' tomorrow.",
            "alerts": "Exit signals detected. Review alerts.json and use 'close' skill if exiting."
        }
    }

    return suggestions[current_skill][result]
```

### 18.2 Future State (Automated with Human-in-Loop)

**Chained execution** (future feature):

```python
def execute_full_pipeline(ticker, archetype):
    """
    Run analyze → score → pause for approval → open (if BUY).
    """
    # Step 1: Analyze
    analyze_result = run_skill("analyze", {"ticker": ticker, "archetype": archetype})

    if not analyze_result.passed:
        return "Kill screens failed. Idea declined."

    # Step 2: Score
    score_result = run_skill("score", {"ticker": ticker})

    if score_result.score >= 8.25:
        # Pause for user approval
        approval = ask_user(f"""
        {ticker} scored {score_result.score} (BUY).

        Position details:
        - Size: {score_result.position_size}% ({score_result.position_value})
        - Entry: ${score_result.entry_price}
        - Stop: ${score_result.stop_price}
        - Target: ${score_result.target_price}

        Open position?
        A) Yes - open now
        B) No - keep in watchlist
        C) Modify size/parameters
        """)

        if approval == "A":
            open_result = run_skill("open", {"ticker": ticker, **score_result.params})
            return f"Position opened: {open_result.trade_id}"
        else:
            return "Position declined. Watchlist updated."

    elif 6.5 <= score_result.score < 8.25:
        return f"Score {score_result.score} is CONDITIONAL. Manual review required."
    else:
        return f"Score {score_result.score} < 6.5 (PASS). Idea declined."
```

**Daily routine meta-skill** (future):

```python
def morning_routine():
    """
    Execute: regime → monitor → scan (future automation).
    """
    print("Running morning routine...")

    # 1. Update regime
    regime_result = run_skill("regime")
    print(f"Regime: VIX {regime_result.vix}, {regime_result.action}")

    # 2. Monitor active positions
    monitor_result = run_skill("monitor")
    print(f"Monitored {monitor_result.trades_count} positions. Alerts: {len(monitor_result.alerts)}")

    # 3. Scan for new events
    scan_result = run_skill("scan")
    print(f"Found {scan_result.new_events_count} new events.")

    # Summary
    return {
        "regime": regime_result,
        "monitoring": monitor_result,
        "scan": scan_result
    }
```

---

## 19. Implementation Priorities

### 19.1 Phase 1: Core Skills (Current)

**Must have:**
- ✅ `screen` - Kill screens only
- ✅ `analyze` - Full analysis with watchlist creation
- ✅ `score` - 6-filter scoring
- ✅ `open` - Position opening with sizing
- ✅ `monitor` - Daily monitoring with exit signals
- ✅ `close` - Position closing with post-mortem
- ✅ `regime` - VIX/credit spread updates
- ✅ `scan` - Event discovery
- ✅ `review` - Weekly/monthly reports

**Core infrastructure:**
- ✅ JSON schemas for rules
- ✅ Trade lifecycle (active → closed/wins or losses)
- ✅ Logging per skill
- ✅ Alert system (alerts.json)

### 19.2 Phase 2: Enhanced Intelligence

**Add:**
- 🔄 Precedent confidence scoring (tentative → established → framework rule)
- 🔄 Portfolio-level correlation detection
- 🔄 Context-aware precedent matching
- 🔄 Scoring drift tracking across time
- 🔄 Time-aware info parity triggers
- 🔄 Graduated exit thresholds
- 🔄 Multi-catalyst milestone tracking

### 19.3 Phase 3: Automation

**Add:**
- ⏳ Chained skill execution with checkpoints
- ⏳ Morning routine meta-skill
- ⏳ Scheduled scanning (weekly event discovery)
- ⏳ Auto-archiving of past catalysts
- ⏳ Framework pattern detection and schema update suggestions

**Note:** All automation requires human-in-loop approval. Never fully autonomous.

---

## 20. Data Sources & APIs

### 20.1 Required Data Sources

| Data Type | Primary Source | Fallback | Update Frequency |
|-----------|----------------|----------|------------------|
| Price | IBKR Paper API | Stooq, Yahoo Finance | Real-time / 15min delay |
| Financials | SEC EDGAR API | Manual 10-Q/10-K parsing | Quarterly |
| PDUFA Dates | FDA DAF Calendar | BioPharmCatalyst | Weekly |
| 13D Filings | SEC EDGAR RSS | 13DMonitor | Daily (future) |
| Merger Deals | Web search, 8-K filings | Manual entry | As announced |
| VIX / Credit | CBOE, FRED | Yahoo Finance | Daily |
| News/Media | Web search | Manual review | On-demand |

### 20.2 Data Refresh Logic

```python
DATA_REFRESH_POLICY = {
    "price": {
        "cache_duration": "1 hour",
        "critical_operations": ["monitor", "open", "close"],  # Fetch fresh
        "non_critical": ["screen", "analyze"]  # Cache OK
    },
    "financials": {
        "cache_duration": "90 days",
        "invalidate_on": ["new_filing_detected", "restatement", "user_request"],
        "validate_on_fetch": True  # Check M-Score/Z-Score ranges
    },
    "events": {
        "cache_duration": "7 days",
        "scan_frequency": "manual",  # Future: weekly scheduled
        "archive_past": True
    }
}
```

---

## 21. File System Structure

```
idiosyncratic-investment/
├── CONFIG.json                 # Account, regime, risk params
├── FRAMEWORK.md                # Human-readable framework rules
├── TECHNICAL_SPEC.md           # This document
├── CLAUDE.md                   # Agent instructions
│
├── schema/                     # Machine-readable rules
│   ├── archetypes.json
│   ├── kill_screens.json
│   ├── scoring.json
│   ├── exits.json
│   └── CHANGELOG.md            # Schema version history
│
├── universe/                   # Idea pipeline
│   ├── events.json             # Upcoming catalysts
│   ├── events_archive.json     # Past catalysts
│   ├── watchlist/              # Active investigations
│   │   └── TICKER.md
│   └── screened/               # Monthly screening logs
│       └── 2025-01.json
│
├── trades/                     # Decision traces
│   ├── active/                 # Open positions
│   │   └── TRD-YYYYMMDD-TICKER-ARCH.json
│   ├── closed/
│   │   ├── wins/              # Profitable trades
│   │   │   └── TRD-YYYYMMDD-TICKER-ARCH.md
│   │   └── losses/            # Losing trades
│   │       └── TRD-YYYYMMDD-TICKER-ARCH.md
│   ├── conditional/           # CONDITIONAL scores declined
│   │   └── TRD-YYYYMMDD-TICKER-ARCH.json
│   └── passed/                # Failed kill screens / PASS scores
│       └── YYYY-MM-DD-TICKER-ARCH.json
│
│
├── logs/                      # Execution logs
│   ├── screen/
│   │   └── 2025-01-05.log
│   ├── analyze/
│   │   └── 2025-01-05.log
│   ├── score/
│   │   └── 2025-01-05.log
│   ├── monitor/
│   │   └── 2025-01-05.log
│   ├── open/
│   │   └── 2025-01-05.log
│   └── close/
│       └── 2025-01-05.log
│
├── alerts.json                # Active alerts requiring action
├── alerts_archive.json        # Acknowledged alerts
│
├── scripts/                   # Integration scripts
│   └── ibkr_paper.py          # IBKR paper trading API
│
└── .codex/skills/             # Claude Code skills
    ├── screen/
    ├── analyze/
    ├── score/
    ├── open/
    ├── monitor/
    ├── close/
    ├── regime/
    ├── scan/
    └── review/
```

---

## 22. Agent Communication Examples

### 22.1 Kill Screen Context

**Good: Provides context and precedents**

```
MSFT fails market cap ceiling ($3.1T > $75B legislative threshold).

Context:
- Framework targets underappreciated special situations
- Mega-caps ($50B+) are widely analyzed by institutions
- Lower opportunity density for idiosyncratic edge

Precedents:
- TRD-2024-045 (AAPL): Overrode cap, returned +2% (marginal)
- TRD-2024-062 (GOOGL): Overrode cap, returned -5% (thesis overwhelmed by macro)

Pattern (n=2): Mega-cap legislative plays underperformed (avg +0.5% vs +12.3% framework avg)

Recommendation: Auto-PASS, logged to screened/

Override kill screen?
```

**Bad: Just auto-fails without context**
```
MSFT fails market cap ceiling. Auto-PASS.
```

### 22.2 Scoring Edge Case

**Good: Auto-decides with rationale**

```
SRPT scored 8.2 (just below 8.25 BUY threshold).

Decision: CONDITIONAL (auto-classified)

Scoring breakdown:
- Catalyst: 2.0 (PDUFA date confirmed)
- Mispricing: 1.5 (modest gap to fair value)
- Noise Survival: 2.0 (strong balance sheet)
- Downside Floor: 1.5 (asset value support)
- Risk/Reward: 1.2 (2.5:1 ratio)
- Info Half-Life: 0.0 (widely covered)

Next step: Review thesis and confirm if opening position.
```

### 22.3 Exit Signal

**Good: Asks at exact threshold**

```
TRD-2025-001 (SRPT) info parity = 2.0 (exact threshold)

Signals triggered:
- Media: 2 mainstream articles (WSJ, Bloomberg)
- IV: Options IV 2.1x average
- Price: 48% to target ($177 current, $180 target)

Weighted sum: 2.0 (50% exit threshold)

Current position:
- Entry: $125.50 (7 days ago)
- Current: $177.00
- Unrealized gain: +41%

Exit 50% of position?
A) Yes - exit 50% (lock in gains)
B) No - hold (wait for full 3.0 exit)
C) Full exit now (take profits early)
```

### 22.4 Data Source Failure

**Good: Retries, notifies clearly, stops**

```
Attempting to screen AQST...

Data fetch attempts:
✓ SEC API: Connected
✗ SEC financials: Rate limited (429 error)
✓ Alternative: Yahoo Finance financials
✗ M-Score calculation: Missing SGAI component

Cross-check attempts:
✗ Stooq: No financial data available
✗ Manual 10-Q parsing: Q3 2024 filed, but missing depreciation breakout

Status: Cannot calculate M-Score (missing data)

Action: Logged to screened/ as "data_unavailable"

Manual review needed: Check 10-Q manually or wait for data source recovery
```

---

## 23. Testing & Validation Checklist

### 23.1 Kill Screen Validation

- [ ] M-Score calculation matches manual calculation from 10-K
- [ ] Z-Score calculation matches manual calculation
- [ ] Industry-adjusted Z-Score thresholds applied correctly
- [ ] PDUFA financial health screens all validated (cash runway, D/E, net cash, gross margin)
- [ ] Market cap ceiling varies by archetype (merger $100B, legislative $75B, default $50B)
- [ ] Data source fallback works (SEC → Yahoo → manual)

### 23.2 Scoring Validation

- [ ] 6 filters sum correctly (max 11 points)
- [ ] Archetype adjustments apply correctly (activist +1.0, legislative -1.5, etc.)
- [ ] Scoring drift tracked across time
- [ ] Previous scores shown as reference (if available)
- [ ] Thresholds enforced (8.25 BUY, 6.5-8.24 CONDITIONAL, <6.5 PASS)

### 23.3 Position Sizing Validation

- [ ] Kellner rule enforced (max 2% portfolio loss)
- [ ] Archetype caps enforced (merger 3%, PDUFA 1.5%, activist 6%, etc.)
- [ ] Kelly fraction applied correctly (25% negative skew, 50% positive skew)
- [ ] Binding constraint logged in trade JSON
- [ ] Stop loss calculated correctly per archetype

### 23.4 Info Parity Validation

- [ ] Media trigger counts only mainstream outlets
- [ ] Time-aware filtering (ignore pre-catalyst PDUFA speculation)
- [ ] IV calculated correctly (>2x average)
- [ ] Price move to target calculated correctly (>50%)
- [ ] Archetype-specific weights applied (PDUFA: media 0.5, IV 1.5, price 1.0)
- [ ] Weighted sum calculated correctly
- [ ] Graduated exit thresholds work (2.0 = 50%, 3.0 = full)

### 23.5 Trade Lifecycle Validation

- [ ] Trade ID format correct (TRD-YYYYMMDD-TICKER-ARCH)
- [ ] Active trade JSON has all required fields
- [ ] Post-mortem generated with precedent links and scoring drift
- [ ] Closed trade moved to wins/ or losses/ correctly
- [ ] CONDITIONAL declines go to conditional/ directory
- [ ] PASS decisions logged to passed/

### 23.6 Error Handling Validation

- [ ] Data source fallback works (IBKR → Stooq → Yahoo)
- [ ] Partial monitoring failures complete successfully, alert about failures
- [ ] Anomalous data cross-checked (M-Score >10, price <$0.10)
- [ ] Retry logic works (wait 30min, adjust limit, retry entry orders)

---

## 24. Glossary

### 24.1 Key Terms

**Agent:** Claude Code skill that autonomously executes framework logic

**Archetype:** One of 7 special situation categories (Merger Arb, PDUFA, Activist, Spin-off, Liquidation, Insider, Legislative)

**Binding Constraint:** Which rule limited position size (Kellner, Archetype Cap, or Kelly)

**Cockroach Rule:** "First regulatory delay, financing wobble, or board dissent → EXIT"

**CONDITIONAL:** Score 6.5-8.24, requires additional confirmation before opening

**Info Parity:** When mainstream market learns your thesis (media coverage, IV spike, price move)

**Kellner Rule:** Max 2% portfolio loss per trade

**Kill Screen:** Binary pass/fail gate (M-Score, Z-Score, etc.) that auto-fails ideas

**Milestone:** Sequential catalyst in multi-stage trade (NDA acceptance, AdCom, PDUFA)

**Precedent:** Past trade used for pattern matching and decision context

**Scoring Drift:** Change in score over time for same ticker (tracked for learning)

**Soft Thesis Break:** Thesis weakens but doesn't fully break (suggests 50% exit)

**Weighted Sum:** Info parity calculation: (media × weight) + (IV × weight) + (price × weight)

### 24.2 Archetype Abbreviations

- **MA:** Merger Arb
- **PD:** PDUFA
- **AC:** Activist
- **SP:** Spin-off
- **LQ:** Liquidation
- **IN:** Insider
- **LG:** Legislative

## 25. Appendix: Decision Flow Diagrams

### 25.1 Idea Screening Flow

```
New Idea
    ↓
Run Kill Screens (screen skill)
    ↓
PASS? ───No──→ Log to passed/ ───→ END
    ↓ Yes
Run 6-Filter Scoring (score skill)
    ↓
Score ≥ 8.25? ───Yes──→ BUY ───→ Open Position
    ↓ No
Score ≥ 6.5? ───Yes──→ CONDITIONAL ───→ User Review ───→ Open or Decline
    ↓ No
PASS ───→ Log to passed/ ───→ END
```

### 25.2 Daily Monitoring Flow

```
Morning (User Invokes)
    ↓
Run regime skill ───→ Update VIX, Credit Spreads ───→ Check Alerts
    ↓
Run monitor skill for each active trade
    ↓
Check Hard Exits First:
  - Cockroach? ───Yes──→ ALERT: Exit Immediately
  - Thesis Break? ───Yes──→ ALERT: Exit Immediately
    ↓ No
Calculate Info Parity:
  - Media (2+ articles)
  - IV (>2x average)
  - Price (>50% to target)
    ↓
Weighted Sum ≥ 3.0? ───Yes──→ ALERT: Full Exit
    ↓ No
Weighted Sum ≥ 2.0? ───Yes──→ ALERT: Exit 50% (ask user)
    ↓ No
Below 200-day MA? ───Yes──→ NOTE: Defensive posture
    ↓ No
HOLD ───→ Log monitoring entry ───→ Continue
```

### 25.3 Position Opening Flow

```
Score ≥ 8.25 (BUY Decision)
    ↓
Calculate Position Size:
  1. Kelly Fraction (25% or 50%)
  2. Archetype Cap (1.5% to 10%)
  3. Kellner Rule (2% max loss)
    ↓
Take Minimum (Most Conservative)
    ↓
Log Binding Constraint
    ↓
Generate Trade ID: TRD-YYYYMMDD-TICKER-ARCH
    ↓
Create Active Trade JSON
    ↓
Place Limit Order (bid/ask midpoint)
    ↓
Wait 30 Minutes
    ↓
Filled? ───Yes──→ Log Entry, Update Trade JSON ───→ END
    ↓ No
Adjust Limit (New Midpoint)
    ↓
Retry Order
    ↓
Filled? ───Yes──→ Log Entry ───→ END
    ↓ No
Price Moved >5%? ───Yes──→ Cancel, Mark "Missed Entry" ───→ END
    ↓ No
Ask User: Retry or Cancel?
```
---

## 26. IBKR Position Reconciliation

### 26.1 Overview

IBKR position reconciliation ensures that the framework's trade files (`trades/active/*.json`) remain synchronized with actual broker positions. This section defines the detection logic, auto-create templates, reconciliation actions, and error handling.

### 26.2 Discrepancy Detection Logic

#### 26.2.1 Reconciliation Workflow

```
1. Fetch IBKR Positions
   └→ Call: IBKRApp.reqPositions() via scripts/ibkr_paper.py
   └→ Returns: List of positions with ticker, quantity, avgCost, account

2. Load Framework Trade Files
   └→ Read all: trades/active/*.json
   └→ Extract: ticker, shares/contracts, entry_price, trade_id

3. Match Positions
   └→ Primary key: ticker (case-insensitive)
   └→ Handle: Multiple positions per ticker (require manual resolution)

4. Detect Discrepancies
   ├─ Orphan IBKR Position: ticker in IBKR, no matching trade file
   ├─ Orphan Trade File: trade file exists, ticker not in IBKR
   ├─ Quantity Mismatch: ticker matches, but shares ≠ IBKR quantity
   └─ Price Drift: entry_price vs avgCost difference (informational only)

5. Generate Reconciliation Report
   └→ Log to: logs/reconciliation/YYYY-MM-DD.log
   └→ Alert to: alerts.json (if alert_threshold met)
```

#### 26.2.2 Discrepancy Types

| Discrepancy | Detection | Severity | Default Action |
|-------------|-----------|----------|----------------|
| **Orphan IBKR Position** | ticker in IBKR, no trade file | HIGH | Alert + ask to create trade file |
| **Orphan Trade File** | trade file exists, no IBKR position | MEDIUM | Alert only (may be pending order) |
| **Quantity Mismatch** | shares/contracts differ | MEDIUM | Alert + ask to update trade file |
| **Price Drift** | entry_price ≠ avgCost | LOW | Log only (expected from limit fills) |

### 26.3 Auto-Create Trade File Template

When an orphan IBKR position is detected and user approves auto-creation:

**Template Specification:**

```json
{
  "trade_id": "TRD-{current_date}-{TICKER}-UNKNOWN",
  "ticker": "{TICKER}",
  "archetype": "unknown",
  "status": "active",
  "thesis": {
    "summary": "AUTO-GENERATED: Position found in IBKR without trade file. Requires manual entry.",
    "catalyst": "UNKNOWN - ENTER MANUALLY",
    "catalyst_date": null,
    "linked_event": null
  },
  "scoring": {
    "final_score": 0,
    "breakdown": {},
    "note": "Position opened outside idiosyncratic system. Score unknown."
  },
  "decision": {
    "action": "RECONCILED_FROM_IBKR",
    "date": "{current_date}",
    "rationale": "Position exists in IBKR but no trade file found. Auto-created for tracking."
  },
  "position": {
    "entry_date": "UNKNOWN",
    "entry_price": "{ibkr_avgCost}",
    "shares": "{ibkr_quantity}",
    "cost_basis": "{ibkr_avgCost * ibkr_quantity}",
    "size_percent": "{cost_basis / account_size}",
    "order_id": null,
    "ibkr_account": "{ibkr_account}",
    "source": "ibkr_reconciliation"
  },
  "exit_plan": {
    "target_price": null,
    "stop_price": null,
    "info_parity_weights": {
      "media": 1.0,
      "iv": 1.0,
      "price": 1.0
    },
    "thesis_break_triggers": ["ENTER MANUALLY"]
  },
  "monitoring": [
    {
      "date": "{current_date}",
      "price": "{current_price}",
      "action": "RECONCILED",
      "notes": "Auto-created from IBKR position during reconciliation. Thesis and archetype require manual entry."
    }
  ]
}
```

**File Naming**: `TRD-{YYYYMMDD}-{TICKER}-UNKNOWN.json`

**Post-Creation Actions**:
1. Write to `trades/active/`
2. Log to `logs/reconciliation/YYYY-MM-DD.log`
3. Alert to `alerts.json` with priority "immediate"
4. User must manually edit: `archetype`, `thesis`, `catalyst`, `exit_plan.thesis_break_triggers`

### 26.4 Reconciliation Action Mapping

Configured via `CONFIG.json → automation.ibkr_reconciliation.reconciliation_actions`:

```json
{
  "reconciliation_actions": {
    "orphan_ibkr_positions": "alert_and_ask",
    "orphan_trade_files": "alert_only",
    "quantity_mismatches": "alert_and_reconcile",
    "price_drift": "log_only"
  }
}
```

**Action Definitions:**

| Action | Behavior |
|--------|----------|
| `alert_and_ask` | Display reconciliation table, ask user for confirmation before action |
| `alert_only` | Write to alerts.json, no automatic changes |
| `alert_and_reconcile` | Ask user, if confirmed → update trade file with IBKR data |
| `log_only` | Log to reconciliation report, no alert |
| `auto_create` | Create trade file automatically without asking (use with caution) |
| `auto_archive` | Move orphan trade file to trades/passed/ with note |

### 26.5 Error Handling

#### 26.5.1 IBKR API Failures

**Connection Errors:**
```
Error: IBKR API connection failed (127.0.0.1:4002)
Action:
1. Check if TWS/Gateway is running
2. Verify port 4002 is correct (paper trading)
3. Retry connection with 30-second timeout
4. If 3 consecutive failures → Alert user, skip reconciliation
5. Log error to logs/reconciliation/YYYY-MM-DD.log
```

**Data Fetch Errors:**
```
Error: reqPositions() returned empty or incomplete data
Action:
1. Validate response structure (check for required fields)
2. If empty but expected positions → Alert user ("IBKR returned no positions")
3. If partial data → Use what's available, log missing fields
4. Never auto-create from incomplete data
```

#### 26.5.2 Multiple Positions Per Ticker

**Scenario**: IBKR has 2 positions for same ticker (e.g., bought at different times)

**Handling**:
```
Error: Multiple IBKR positions found for {TICKER}
Action:
1. Display both positions with avgCost and quantity
2. Do NOT auto-match to trade file
3. Alert user: "Manual resolution required"
4. User must manually:
   - Create separate trade files for each position, OR
   - Consolidate in IBKR before reconciliation
```

#### 26.5.3 Options Positions

**Scenario**: IBKR position is options contract, trade file expects equity

**Handling**:
```
Detection:
- IBKR secType == "OPT" vs trade file has "shares" field

Action:
1. Check if trade file has "contracts" field (options trade)
2. If mismatch (equity file, options IBKR):
   └→ Alert: "Position type mismatch: equity file vs options IBKR"
   └→ Manual resolution required
3. If both options:
   └→ Match by strike + expiration (not just ticker)
```

### 26.6 Reconciliation Frequency

**Daily (Optional)**:
- Quick check: orphan positions only
- Action: Alert, no auto-create
- Timing: After monitor step in daily.md (Step 8)

**Weekly (Recommended)**:
- Full reconciliation: all discrepancy types
- Action: Alert + ask for auto-create
- Timing: Step 4 in weekly.md
- Output: Full report to logs/reconciliation/

**On-Demand**:
- Manual: `python scripts/ibkr_paper.py positions --reconcile`
- Use when: Suspecting sync issues, after manual trades in IBKR, before important decisions

### 26.7 Configuration Reference

**Full CONFIG.json Section:**

```json
{
  "automation": {
    "ibkr_reconciliation": {
      "enabled": false,
      "frequency": "weekly",
      "auto_create_from_ibkr": false,
      "alert_threshold": "any",
      "reconciliation_actions": {
        "orphan_ibkr_positions": "alert_and_ask",
        "orphan_trade_files": "alert_only",
        "quantity_mismatches": "alert_and_reconcile",
        "price_drift": "log_only"
      },
      "error_handling": {
        "connection_timeout_seconds": 30,
        "max_retry_attempts": 3,
        "skip_on_failure": true,
        "alert_on_connection_failure": true
      },
      "options_handling": {
        "match_by_strike_expiration": true,
        "allow_auto_create_options": false
      }
    }
  }
}
```

**Key Settings:**
- `enabled`: Run reconciliation (daily or weekly based on frequency)
- `frequency`: "daily" | "weekly" | "manual"
- `auto_create_from_ibkr`: Auto-create trade files without asking (default: false for safety)
- `alert_threshold`: "any" (all discrepancies) | "critical" (only orphans + qty mismatches)

### 26.8 Implementation Notes

**Future Enhancements:**
1. **Order ID Linking**: Store IBKR permId in trade files for precise matching
2. **Real-time Sync**: WebSocket connection for instant position updates
3. **Two-Way Sync**: Close IBKR positions when trade files are archived
4. **Batch Reconciliation**: Process multiple discrepancies with single confirmation
5. **Historical Reconciliation**: Compare past trades with IBKR executions report

**Testing Checklist:**
- [ ] Test orphan IBKR position detection and auto-create
- [ ] Test orphan trade file detection (pending order scenario)
- [ ] Test quantity mismatch reconciliation
- [ ] Test IBKR connection failure handling
- [ ] Test multiple positions per ticker handling
- [ ] Test options position reconciliation
- [ ] Test reconciliation report generation
- [ ] Verify alerts.json writes with correct priority

---
