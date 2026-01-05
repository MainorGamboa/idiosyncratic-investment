# Workflow Automation Commands

This directory contains slash commands to automate common skill execution workflows in the idiosyncratic trading system.

## Available Commands

### Daily Operations

**`/daily`** - Morning routine
- Updates regime (VIX, credit spreads)
- Monitors all active trades
- Shows alerts and action items
- **When**: Every market day before 9:30 AM ET

**`/quick-check`** - Fast status check
- Shows regime state
- Monitors positions
- Displays alerts and P&L
- **When**: Intraday or after significant market moves

### Discovery & Research

**`/discover`** - Find new catalyst events
- Scans FDA PDUFA calendar, SEC 13D filings, merger announcements
- Updates universe/events.json with new catalysts
- Displays newly discovered opportunities by archetype
- Prompts to analyze promising tickers
- **When**: Weekly to maintain 8-12 active catalyst events

### Analysis & Entry

**`/analyze-idea TICKER`** - Analysis pipeline (no position opening)
- Kill screens → Analyze → Score
- Displays recommendation (BUY/CONDITIONAL/PASS)
- Prompts to open position if BUY (but doesn't auto-open)
- **When**: Want to analyze without committing to open position yet

**`/new-trade TICKER`** - Complete end-to-end workflow
- Kill screens → Analyze → Score → Open position
- Auto-opens if BUY (≥8.25), asks confirmation if CONDITIONAL
- Creates active trade in trades/active/
- **When**: Ready to go from idea to position in one command

**`/open-position TICKER`** - Open position from scored watchlist
- Opens position from already-analyzed ticker
- Requires existing watchlist file with score
- **When**: Already ran `/analyze-idea`, now ready to open position

### Exit & Close

**`/close-trade TRADE_ID`** - Close position
- Closes position, calculates P&L
- Creates post-mortem
- Updates precedents
- **When**: Exit signal ≥2.0, catalyst occurs, stop loss hit

### Weekly Maintenance

**`/weekly-review`** - End of week review
- Generates review report
- Scans for new catalysts
- Checks stale watchlist items
- **When**: Friday after close or Sunday evening

## Command Design Principles

1. **Simple & focused**: Each command does one workflow
2. **Skill composition**: Commands chain existing skills, don't duplicate logic
3. **User confirmation**: Commands prompt before high-stakes actions (opening/closing positions)
4. **Fail-fast**: Stop immediately on kill screen failures
5. **Traceable**: All decisions logged to appropriate directories

## Typical Workflows

### Daily Workflow
```
Morning:
  /daily                    # Update regime + monitor positions

During market hours:
  /new-trade TICKER         # New opportunity → open position
  /quick-check              # After significant market moves

End of day:
  /close-trade TRADE_ID     # If exit signal triggered
```

### Weekly Workflow
```
Sunday evening or Friday after close:
  /weekly-review            # Generate review + scan catalysts
  /discover                 # Find new opportunities for the week
```

### New Idea Workflows

**Option 1: Cautious (analyze first, decide later)**
```
/analyze-idea TICKER        # Just analyze and score
# Review the thesis and score...
/open-position TICKER       # Open if you like it
```

**Option 2: Aggressive (go from idea to position)**
```
/new-trade TICKER           # Complete workflow: analyze → open
```

## Manual Skill Invocation

You can still invoke skills directly for specific use cases:

- `/skill regime` - Just update market regime
- `/skill screen TICKER` - Fast kill screen check only
- `/skill search TAGS` - Find similar precedent trades
- `/skill scan` - Update catalyst calendar only

## Extending Workflows

To add new commands:
1. Create `.claude/commands/your-command.md`
2. Describe the workflow steps clearly
3. Specify when to use it
4. Keep it simple and focused on one workflow

Commands are just markdown files that prompt Claude Code to execute a sequence of skills. The simpler, the better.
