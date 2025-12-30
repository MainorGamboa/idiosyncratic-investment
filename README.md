# Idiosyncratic Trading System

A structured system for catalyst-driven special situations investing.

## Structure

```
idiosyncratic/
├── FRAMEWORK.md              # Human-readable framework (authoritative)
├── CONFIG.json               # Account size, risk params, regime state
│
├── schema/                   # Machine-readable rules
│   ├── archetypes.json       # 7 archetypes with base rates
│   ├── kill_screens.json     # Kill screen definitions
│   ├── scoring.json          # 6 filters + adjustments
│   └── exits.json            # Exit rules, info parity
│
├── universe/                 # What you're tracking
│   ├── events.json           # Upcoming catalysts
│   ├── watchlist/            # Ideas under investigation
│   └── screened/             # Kill screen results log
│
├── trades/                   # Decision traces
│   ├── active/               # Current positions
│   ├── closed/               # Completed trades
│   └── passed/               # Documented PASS decisions
│
├── journal/                  # Narrative layer
│   └── reviews/              # Weekly reviews
│
├── precedents/               # Searchable patterns
│   ├── index.json            # Tag → trade mappings
│   └── patterns.md           # Named patterns
│
└── skills/                   # Claude Code skills
    ├── analyze/              # Full framework analysis
    ├── screen/               # Kill screens only
    ├── score/                # 6-filter scoring
    ├── open/                 # Open new position
    ├── monitor/              # Update active trades
    ├── close/                # Close position
    ├── regime/               # Check market regime
    ├── search/               # Find precedents
    ├── scan/                 # Find new events
    └── review/               # Generate reports
```

## Quick Start

### 1. Update Regime (Daily)
```
→ regime skill
→ Updates CONFIG.json with VIX, credit spreads
```

### 2. Analyze New Idea
```
→ screen skill (quick kill screen check)
→ If passed: analyze skill (full analysis)
→ If BUY: score skill (complete scoring)
```

### 3. Open Position
```
→ open skill
→ Creates trades/active/{TRADE_ID}.json
```

### 4. Monitor Positions
```
→ monitor skill (daily)
→ Checks info parity, hard exits
→ Returns alerts if action needed
```

### 5. Close Position
```
→ close skill
→ Moves to trades/closed/
→ Adds outcome + post-mortem
```

## Key Files

| File | Purpose |
|------|---------|
| `FRAMEWORK.md` | Human-readable rules |
| `CONFIG.json` | System state (update daily) |
| `schema/*.json` | Machine-readable rules |
| `precedents/patterns.md` | Named patterns from experience |

## Design Principles

1. **JSON for data, MD for narrative**
2. **Skills as verbs** — each does one thing
3. **IDs link everything** — trades reference events
4. **Flat over nested** — max 2 levels deep
5. **Decision traces compound** — even PASS decisions get logged

## Framework Version

v3.6 (December 2024) — Backtest-Validated
