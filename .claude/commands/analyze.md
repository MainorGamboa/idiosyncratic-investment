# Analyze Specific Ticker

When you have a specific ticker you want to analyze (outside of automated daily cycle):

## Workflow

1. Run `screen` skill → Kill screens
   - If FAIL: Log to trades/passed/ and EXIT

2. Run `analyze` skill → Create watchlist file

3. Run `score` skill → Generate BUY/CONDITIONAL/PASS

4. If BUY (≥8.25): Auto-open position
   - If CONDITIONAL (6.5-8.24): Ask user for confirmation
   - If PASS (<6.5): Log and exit

## When to Use

- User has specific ticker idea outside automated scans
- Want to manually investigate a ticker
- Testing a thesis

## Example

```
/analyze SRPT
```

This is the ONLY manual command needed besides /daily and /weekly.
