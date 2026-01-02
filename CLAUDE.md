# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an idiosyncratic trading system for catalyst-driven special situations investing. The system uses a structured framework with 7 archetypes (Merger Arb, PDUFA, Activist, Spin-off, Liquidation, Insider, Legislative), kill screens, scoring filters, and exit protocols. All logic is codified in JSON schemas and executed through Claude Code skills.

## Core Architecture

### Data Flow & Decision Pipeline

```
KILL SCREENS → SCORE (6 Filters) → SIZE → ENTER → MONITOR → EXIT
```

The system separates **data** (JSON) from **narrative** (Markdown):
- **JSON**: Machine-readable rules, trade state, scoring thresholds (`CONFIG.json`, `schema/*.json`, `trades/active/*.json`)
- **Markdown**: Human-readable explanations, theses, post-mortems (`FRAMEWORK.md`, `universe/watchlist/*.md`, `trades/closed/*.md`)

### Directory Structure & Purpose

```
schema/              # Authoritative rules (DO NOT modify without user approval)
├── archetypes.json  # 7 archetypes: base rates, position sizing, entry timing
├── kill_screens.json # Binary pass/fail gates (M-Score, Z-Score, etc.)
├── scoring.json     # 6 filters (max 11 pts) + archetype adjustments
└── exits.json       # Info parity signals + hard exit triggers

universe/            # What you're tracking
├── events.json      # Upcoming catalyst calendar
├── watchlist/       # Ideas under investigation (*.md files)
└── screened/        # Monthly kill screen results log

trades/              # Decision traces (all JSON)
├── active/          # Current positions with exit plans
├── closed/          # Completed trades with post-mortems
└── passed/          # Documented PASS decisions (for learning)

precedents/          # Searchable pattern library
├── index.json       # Tag → trade_id mappings
└── patterns.md      # Named patterns from closed trades
```

### Key Constraints

1. **Flat over nested**: Maximum 2 directory levels. No deeply nested structures.
2. **IDs link everything**: Trades reference event IDs; precedents reference trade IDs.
3. **Decision traces compound**: Even PASS decisions are logged in `trades/passed/` for future learning.
4. **Schema is authoritative**: `FRAMEWORK.md` is human-readable, but `schema/*.json` files are the machine-executable truth.

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
| `search` | Find similar trades by tags/text | Before scoring new ideas (find precedents) |
| `scan` | Find new catalyst events from FDA/SEC/etc. | Weekly to maintain catalyst calendar |
| `review` | Generate weekly/monthly review report | End of week/month or after significant events |

### Skill Execution Flow

**Typical workflow for a new idea:**
```
1. scan (find catalyst) → updates universe/events.json
2. analyze TICKER (kill screens) → creates universe/watchlist/TICKER.md
3. score TICKER → updates watchlist with final score
4. open TICKER (if BUY) → creates trades/active/{TRADE_ID}.json
5. monitor (daily) → checks exit signals
6. close TRADE_ID (when triggered) → moves to trades/closed/, updates precedents/index.json
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

- **Framework Version**: 3.6 (December 2024, backtest-validated)
- **Account Size**: Set in `CONFIG.json` (default $25,000)
- **Regime State**: Updated daily via `regime` skill
  - VIX levels: <20 (normal), 20-30 (elevated), >30 (sustained crisis)
  - HY OAS: Widening >100bp triggers merger arb reduction

## Important Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `FRAMEWORK.md` | Human-readable framework rules | Rarely (framework updates) |
| `CONFIG.json` | Account size, risk params, regime state | Daily (regime), rarely (config) |
| `schema/*.json` | Machine-readable rules | Rarely (framework updates) |
| `universe/events.json` | Upcoming catalyst calendar | Weekly via `scan` skill |
| `precedents/patterns.md` | Named patterns from experience | After closing trades |

## Data Sources & Integration

Skills fetch external data via web search and APIs:
- **Price data**: Stooq (`stooq.com/q/d/l/?s={ticker}.us&i=d`)
- **SEC filings**: `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
- **FDA catalysts**: `www.accessdata.fda.gov/scripts/cder/daf/`
- **News/media**: Web search for mainstream coverage (info parity checks)

## Workflow Notes

- **Skills run autonomously**: User invokes skill by name (e.g., `/analyze SRPT`), skill reads schemas and executes.
- **All decisions must be traceable**: Every trade file contains entry_thesis, scoring_breakdown, exit_plan.
- **Precedents are searchable**: The `search` skill uses `precedents/index.json` to find similar past trades by tags.
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
3. **IDs link everything**: Trades reference events, precedents reference trades.
4. **Flat over nested**: Max 2 levels deep to avoid complexity.
5. **Decision traces compound**: Even PASS decisions are logged for learning.
