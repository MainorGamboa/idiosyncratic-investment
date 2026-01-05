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

### Analysis & Entry

**`/analyze-idea TICKER`** - Full analysis pipeline
- Kill screens → Analyze → Score
- Displays recommendation (BUY/CONDITIONAL/PASS)
- Prompts to open position if BUY
- **When**: New idea discovered or catalyst triggered

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

## Typical Daily Workflow

```
Morning:
  /daily                    # Update regime + monitor positions

During market hours:
  /analyze-idea TICKER      # New opportunity discovered
  /quick-check              # After significant market moves

End of day:
  /close-trade TRADE_ID     # If exit signal triggered

End of week:
  /weekly-review            # Friday/Sunday routine
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
