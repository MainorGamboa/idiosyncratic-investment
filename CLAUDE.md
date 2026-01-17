# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an idiosyncratic trading system for catalyst-driven special situations investing. The system uses a structured framework with 7 archetypes (Merger Arb, PDUFA, Activist, Spin-off, Liquidation, Insider, Legislative), kill screens, scoring filters, and exit protocols. All logic is codified in JSON schemas and executed through Claude Code skills.

## Technical Specification Reference

This file (CLAUDE.md) provides **agent operational guidelines** for Claude Code skills. For detailed technical implementation specifications, refer to:

- **TECHNICAL_SPEC.md**: Authoritative technical reference covering agent autonomy model, data management, error handling, order execution, logging, and advanced features
- **FRAMEWORK.md**: Human-readable framework rules and decision logic
- **schema/*.json**: Machine-executable rules (archetypes, kill screens, scoring, exits)

**Relationship:**
- CLAUDE.md = "How Claude should behave and what to do"
- TECHNICAL_SPEC.md = "How the system works technically"
- FRAMEWORK.md = "Why we make these decisions"
- schema/*.json = "Precise rules and thresholds"

## Core Architecture

### Data Flow & Decision Pipeline

```
KILL SCREENS → SCORE (6 Filters) → SIZE → ENTER → MONITOR → EXIT
```

The system separates **data** (JSON) from **narrative** (Markdown):
- **JSON**: Machine-readable rules, trade state, scoring thresholds (`CONFIG.json`, `schema/*.json`, `trades/active/*.json`)
- **Markdown**: Human-readable explanations, theses, post-mortems (`FRAMEWORK.md`, `universe/watchlist/*.md`, `trades/closed/*.md`)

### Directory Structure & Purpose

**NOTE:** See "File Organization" section below for complete directory structure with new v1.0 organization.

```
schema/              # Authoritative rules (DO NOT modify without user approval)
├── archetypes.json  # 7 archetypes: base rates, position sizing, entry timing
├── kill_screens.json # Binary pass/fail gates (M-Score, Z-Score, etc.)
├── scoring.json     # 6 filters (max 11 pts) + archetype adjustments
├── exits.json       # Info parity signals + hard exit triggers
├── data_sources.json # Tiered sources, calendar triggers, personalities
└── CHANGELOG.md     # Framework version history

universe/            # What you're tracking
├── events.json      # Upcoming catalyst calendar
├── events_archive.json # Past catalysts
├── watchlist/       # Ideas under investigation (*.md files)
└── screened/        # Monthly kill screen results log

trades/              # Decision traces
├── active/          # Current positions with exit plans (JSON)
├── closed/
│   ├── wins/       # Profitable trades (MD post-mortems)
│   └── losses/     # Losing trades (MD post-mortems)
├── conditional/    # CONDITIONAL scores user declined (JSON)
└── passed/         # Failed kill screens / PASS scores (JSON)

logs/                # Execution logs by skill
├── screen/, analyze/, score/, open/, monitor/, close/
├── regime/, scan/, review/
└── Format: YYYY-MM-DD.log

alerts.json          # Active alerts requiring action
alerts_archive.json  # Acknowledged alerts
```

### Key Constraints

1. **Flat over nested**: Maximum 2 directory levels. No deeply nested structures.
2. **IDs link everything**: Trades reference event IDs;
3. **Decision traces compound**: Even PASS decisions are logged in `trades/passed/` for future learning.
4. **Schema is authoritative**: `FRAMEWORK.md` is human-readable, but `schema/*.json` files are the machine-executable truth.

## Agent Autonomy Model

**Core Principles** (see TECHNICAL_SPEC.md §1.1-1.2 for full details):

1. **Ask-first over fail-safe**: When uncertain, interrupt for clarification rather than defaulting conservatively
2. **Context-aware precedents**: Suggest similar past decisions only when factors match (therapeutic area, approval pathway, activist tier, etc.)
3. **Fresh evaluation over consistency**: Always re-score with current data, but track why decisions changed
4. **Cross-checking over trust**: Validate suspicious data across multiple sources automatically
5. **Graduated responses**: Use thresholds and confidence levels rather than binary decisions

### Interruption Guidelines

**Always ask user:**
- Kill screen violations (if agent confidence low or ambiguous case)
- Exit signals at exact threshold (weighted_sum = 2.0)
- Cockroach ambiguity (precedents unclear, severity uncertain)
- High-stakes decisions (kill screen overrides, forced exits)

**Auto-decide (with explanation):**
- Scoring edge cases (8.2 → CONDITIONAL)
- Data source fallbacks (IBKR fails → use Stooq)
- Borderline metrics that are strict but not extreme

**Suggest (don't wait for user):**
- Next skill in workflow ("Run 'score TICKER' to complete analysis")
- Position adjustments on regime change ("VIX >30, consider reducing merger arb")
- Re-scoring when material news detected

## Data Management

**See TECHNICAL_SPEC.md §2 for complete data source strategy and validation protocols.**

### Event-Driven Data Sources (Reference: schema/data_sources.json)

The system uses a tiered data source hierarchy for event discovery and monitoring:

**Free stack (enabled by default in CONFIG.json):**
- SEC EDGAR (Form 4, 13D, 8-K, Form 10)
- OpenInsider (insider cluster detection)
- BioPharmCatalyst (PDUFA dates, AdCom)
- FDA.gov (official approvals/CRLs)
- FTC/DOJ (merger reviews)
- Congress.gov (legislative tracking)
- SPACtrack, CEFConnect (liquidation discounts)
- Clark Street Value (micro-cap liquidation analysis)

**Paid stack (optional, enable in CONFIG.json):**
- InsideArbitrage ($299/yr) - covers 5 archetypes
- STAT News ($299/yr) - PDUFA regulatory analysis
- Barron's ($100-200/yr) - weekly insider column

**Key personalities (manual reference - see schema/data_sources.json):**
- @adamfeuerstein (PDUFA)
- @AsifSuria (merger arb, insider)
- Stock Spinoff Investing / Rich Howe (spin-offs)
- Clark Street Value blog (liquidation)

### Data Source Strategy (Graceful Degradation)

**Price Data:**
1. Try IBKR paper account (real-time)
2. If fails → Stooq (delayed 15min)
3. If fails → Yahoo Finance
4. If all fail → Log error, notify user, halt operation

**Financials (Kill Screens):**
1. SEC API (preferred - pre-calculated aggregated data)
2. Manual calculation from raw 10-Q/10-K
3. Third-party screening tools (fallback)

**Event Data:**
- PDUFA dates: `accessdata.fda.gov/scripts/cder/daf/`
- Activist 13Ds: `sec.gov/cgi-bin/browse-edgar`
- Merger announcements: Web search, SEC 8-K filings
- Legislative: Manual entry

### Data Validation Rules

**Always validate:**
- M-Score expected range: -2 to +2 (flag if >10 or <-10, try alternative source)
- Price anomalies: >50% moves in 1 day, prices <$0.10 (cross-check all sources)
- Z-Score expected range: -5 to +10 (flag extreme outliers)

**Cross-checking protocol:**
- **Always cross-check**: Price anomalies, outlier financial metrics, conflicting data (>5% difference)
- **Single source acceptable**: Normal-range metrics, consistent with historical data

**Borderline handling:**
- Z-Score 1.79 vs threshold 1.81 = FAIL (strict enforcement, no tolerance band)
- M-Score exactly -1.78 = PASS (meets threshold)

## Order Execution

**See TECHNICAL_SPEC.md §10 for complete order execution logic.**

### Entry Orders
- **Default**: Limit order at bid/ask midpoint
- **Rationale**: Better price, acceptable risk of no fill for non-urgent entries
- **Time in force**: DAY

**Retry logic:**
1. Wait 30 minutes if not filled
2. Adjust limit to new midpoint
3. If price moved >5% away, cancel and mark "missed entry"

### Exit Orders
- **Always**: Market orders (immediate execution required)
- **Rationale**: Exit signals demand immediate action, slippage acceptable
- **Time in force**: IOC (Immediate or Cancel)

## Logging & Alerts

**See TECHNICAL_SPEC.md §12, §14 for complete logging and alerting specifications.**

### Logging Structure

Per-skill logs with dates for easy navigation:
```
logs/screen/YYYY-MM-DD.log
logs/analyze/YYYY-MM-DD.log
logs/score/YYYY-MM-DD.log
logs/monitor/YYYY-MM-DD.log
logs/open/YYYY-MM-DD.log
logs/close/YYYY-MM-DD.log
logs/regime/YYYY-MM-DD.log
logs/scan/YYYY-MM-DD.log
logs/review/YYYY-MM-DD.log
```

**Log entry format:**
- Timestamp, skill, ticker, outcome
- Key metrics (M-Score, Z-Score, score, position size, etc.)
- Data sources used
- Execution time
- Notes (why it passed/failed, context)

### Alert System

**Active alerts**: `alerts.json`
**Archived alerts**: `alerts_archive.json`

**Priority levels:**
- **Immediate**: Exit signals (≥2.0), cockroach, stop loss hit, regime change
- **Daily digest**: Monitoring updates (no action needed), P&L summaries
- **Weekly review**: Framework calibration, performance metrics

**Alert persistence**: Write to `alerts.json` + console output. User acknowledges via skill/command, acknowledged alerts archived.

## Working with Skills

Skills are implemented as Claude Code skills in `.codex/skills/` (note: skills also exist in `.claude/skills/` but `.codex/` is the active directory). Each skill does ONE thing:

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `regime` | Update `CONFIG.json` with VIX, credit spreads | Daily before market open |
| `screen` | Run kill screens only (fast) | Quick pass/fail check on new ideas |
| `analyze` | Full analysis: kill screens → watchlist creation | New idea discovered or event triggered |
| `score` | Complete 6-filter scoring → BUY/CONDITIONAL/PASS | After `analyze` has created watchlist file |
| `open` | Open new position from scored idea | After `score` returns BUY or CONDITIONAL with confirmation |
| `monitor` | Check all active trades for exit signals | Daily morning routine or after major moves |
| `close` | Close position, create post-mortem | Exit signal triggered or catalyst occurred |
| `scan` | Find new catalyst events from FDA/SEC/etc. | Weekly to maintain catalyst calendar |
| `review` | Generate weekly/monthly review report | End of week/month or after significant events |

### Commands vs Skills

**Commands** (like `daily`, `weekly`, `bulk-process`) orchestrate multiple skills in a workflow. Commands are NOT skills - they're workflow definitions that live in `.claude/commands/`:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `daily` | Full trading cycle: regime → monitor → close → scan → process pipeline → batch open | Every market day before open |
| `weekly` | Review + deep scan + IBKR reconciliation + calibration | Friday after close or Sunday evening |
| `bulk-process` | Batch scan → screen → analyze → score (NO position management) | Weekly catchup, post-vacation, backlog processing |

**Key differences:**
- **Skills**: Single-purpose, executable actions (e.g., `screen TICKER`, `open TICKER`)
- **Commands**: Multi-skill workflows with decision logic (e.g., `daily` runs regime + monitor + scan + process events)
- **Use bulk-process** for pipeline-only batch processing without opening/closing positions
- **Use daily** for full autonomous trading cycle including position management
- **Use weekly** for maintenance, learning, and reconciliation

### Skill Execution Flow

**Typical workflow for a new idea:**
```
1. scan (find catalyst) → updates universe/events.json
2. analyze TICKER (kill screens) → creates universe/watchlist/TICKER.md
3. score TICKER → updates watchlist with final score
4. open TICKER (if BUY) → creates trades/active/{TRADE_ID}.json
5. monitor (daily) → checks exit signals
6. close TRADE_ID (when triggered) → moves to trades/closed/
```

## Critical Rules

### Kill Screens (Binary Gates)
- **ANY fail = automatic PASS**. Stop immediately.
- **New in v3.7:**
  - Market cap ceiling: $50B base, $100B merger arb, $75B legislative
  - Z-Score industry adjustments: Telecom/biotech 1.5, software 2.0, utilities 2.5
  - PDUFA financial health: 18+ month cash runway, D/E <0.75, net cash position
- Screens vary by archetype (see `schema/kill_screens.json`):
  - All: M-Score > -1.78, Z-Score < threshold (industry-adjusted), Market cap ceiling
  - Merger Arb: Hostile deal, Spread < 2.5%
  - Legislative: Macro conflict
  - PDUFA: Financial health screens (cash runway, leverage, net cash)

### Scoring Thresholds
- **BUY**: ≥8.25 (backtest win rate 68%)
- **CONDITIONAL**: 6.5-8.24 (requires additional confirmation)
- **PASS**: <6.5 (backtest win rate 29%)

### Position Sizing
- **Kellner Rule**: Max 2% portfolio loss per trade
- **Kelly Fraction**: 25% for negative skew (Merger, PDUFA, Activist), 50% for positive skew (Spin-off, Liquidation)
- **Never exceed archetype cap** (e.g., Merger Arb = 3%, PDUFA = 1.5%, Activist = 6%)

### Exit Protocol
1. **Check hard exits FIRST** (Cockroach Rule, Thesis Break, Finerman Corollary)
2. **Then check info parity signals** (media coverage, IV spike, price move >50%)
3. **Weighted sum logic**:
   - <2.0: HOLD
   - ≥2.0: EXIT 50%
   - ≥3.0: FULL EXIT

### Info Parity Weights (Archetype-Specific)
These weights are in `schema/exits.json` under `info_parity.weights_by_archetype`. For example:
- **PDUFA**: media=0.5, iv=1.5, price=1.0 (IV spike is strongest signal)
- **Spin-off**: media=0.5, iv=1.0, price=1.5 (price move is strongest signal)

## Framework Version & State

- **Framework Version**: 1.0 (January 2025, v1 launch)
  - Reset from v3.7 pre-release to v1.0 production
  - See `schema/CHANGELOG.md` for version history
- **Account Size**: Set in `CONFIG.json` (default $25,000)
- **Regime State**: Updated daily via `regime` skill
  - VIX levels: <20 (normal), 20-30 (elevated), >30 (sustained crisis)
  - HY OAS: Widening >100bp triggers merger arb reduction

## File Organization

**See TECHNICAL_SPEC.md §15, §21 for complete file system structure.**

### Trade ID Format

**Standard format**: `TRD-YYYYMMDD-TICKER-ARCHETYPE`

Examples:
- `TRD-20250105-SRPT-PDUFA`
- `TRD-20250110-ABBV-ACTIVIST`
- `TRD-20250115-TRUP-SPINOFF`

Benefits: Readable without opening, sortable by date, grep-friendly

### Directory Structure

```
trades/
├── active/              # Current positions
│   └── TRD-YYYYMMDD-TICKER-ARCH.json
├── closed/
│   ├── wins/           # Profitable trades (post-mortems)
│   │   └── TRD-YYYYMMDD-TICKER-ARCH.md
│   └── losses/         # Losing trades (post-mortems)
│       └── TRD-YYYYMMDD-TICKER-ARCH.md
├── conditional/        # CONDITIONAL scores user declined
│   └── TRD-YYYYMMDD-TICKER-ARCH.json
└── passed/            # Failed kill screens or PASS scores
    └── YYYY-MM-DD-TICKER-ARCH.json

universe/
├── events.json        # Upcoming catalysts
├── events_archive.json # Past catalysts
├── watchlist/         # Ideas under investigation
│   └── TICKER.md
└── screened/          # Monthly kill screen results
    └── YYYY-MM.json

logs/
├── screen/           # Kill screen logs
├── analyze/          # Analysis logs
├── score/            # Scoring logs
├── open/             # Position opening logs
├── monitor/          # Monitoring logs
├── close/            # Closing logs
├── regime/           # Regime update logs
├── search/           # Search logs
├── scan/             # Scanning logs
└── review/           # Review logs

alerts.json           # Active alerts
alerts_archive.json   # Acknowledged alerts
```

## Important Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `TECHNICAL_SPEC.md` | Technical implementation reference | Rarely (major updates) |
| `FRAMEWORK.md` | Human-readable framework rules | Rarely (framework updates) |
| `CLAUDE.md` | Agent operational guidelines (this file) | Rarely (agent behavior) |
| `CONFIG.json` | Account size, risk params, regime state | Daily (regime), rarely (config) |
| `schema/*.json` | Machine-readable rules | Rarely (framework updates) |
| `schema/data_sources.json` | Tiered data sources, calendar triggers, personalities | Rarely (source updates) |
| `schema/CHANGELOG.md` | Framework version history | Each version update |
| `universe/events.json` | Upcoming catalyst calendar | Weekly via `scan` skill |
| `alerts.json` | Active alerts requiring action | Real-time by skills |

## Data Sources & Integration

**See TECHNICAL_SPEC.md §20 and "Data Management" section above for complete data source strategy.**

Skills fetch external data with graceful degradation:

**Price data** (priority order from CONFIG.json):
1. IBKR paper account (real-time) - `127.0.0.1:4002`
2. Stooq (15min delay) - `stooq.com/q/d/l/?s={ticker}.us&i=d`
3. Yahoo Finance (fallback)

**SEC filings**:
- Primary: `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
- Fallback: Manual 10-Q/10-K parsing, third-party tools

**FDA catalysts**:
- `www.accessdata.fda.gov/scripts/cder/daf/`

**News/media**:
- Web search for mainstream coverage (info parity checks)
- Mainstream outlets: WSJ, Bloomberg, FT, CNBC, Reuters, NYT Business

**Cache policy** (from CONFIG.json):
- Price data: 60 minutes
- Financials: 90 days (invalidate on new filing/restatement)
- Events: Manual refresh via `scan` skill

## Workflow Notes

- **Skills run autonomously**: User invokes skill by name (e.g., `/analyze SRPT`), skill reads schemas and executes.
- **All decisions must be traceable**: Every trade file contains entry_thesis, scoring_breakdown, exit_plan.
- **PASS decisions are logged**: Even ideas that fail kill screens or score below 6.5 are logged in `trades/passed/` for learning.
- **Activist sourcing is daily**: Check SEC 13D filings, 13D Monitor, and activist tracker sites daily to maintain 8-12 active events

## Regime-Aware Behavior

When VIX is elevated or credit spreads widen:
- **VIX 20-30**: Reduce new position sizes, widen stops
- **VIX >30 sustained**: Pause all new merger arb positions
- **HY OAS widens 100bp+**: Reduce merger arb proportionally

Check regime state in `CONFIG.json` before opening new positions.

## Archetype-Specific Considerations

### Merger Arb
- 94% success rate for friendly deals
- Enter immediately after announcement
- Watch for third-party veto (-1 adjustment), DOJ/FTC lawsuit (-2 adjustment)

### PDUFA
- 92% approval rate post-NDA
- Max position 1.5% (reduced from 2% due to 2.7x rejection/approval asymmetry)
- Red flags: single-arm studies, trend toward significance, missed primary endpoint

### Activist
- Tier-1 activists (Elliott, Starboard, ValueAct, Pershing Square) = 83% success rate, +1.0 score adjustment
- Tier-2 (Trian, Icahn, Third Point) = 80% success rate, +0.5 adjustment
- Tier-3 (first-timers, small funds) = 40% success rate, no adjustment

### Spin-off
- Enter days 30-60 post-spin (forced index selling creates -2.4% to -3.7% underperformance in first 5 days)
- Year 2 shows peak outperformance

### Legislative
- Primary/obvious beneficiaries get -1.5 penalty (often priced in)
- Secondary/overlooked beneficiaries preferred
- Kill screen: macro conflict (rate/commodity sensitivity that overwhelms legislative tailwind)

## Design Principles

1. **JSON for data, MD for narrative**: Machines read JSON, humans read Markdown.
2. **Skills as verbs**: Each skill does one thing and does it completely.
3. **IDs link everything**: Trades reference events.
4. **Flat over nested**: Max 2 levels deep to avoid complexity.
5. **Decision traces compound**: Even PASS decisions are logged for learning.
