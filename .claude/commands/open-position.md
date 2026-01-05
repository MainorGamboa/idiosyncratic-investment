# Open Position Command

Expects: ticker symbol as argument (e.g., /open-position SRPT)

Open a position from an already-scored ticker in the watchlist:

**Prerequisites**:
- Ticker must have watchlist file in universe/watchlist/TICKER.md
- Ticker must have been scored (BUY or CONDITIONAL decision)

**Workflow**:
1. Verify ticker has been scored (check watchlist file)
2. If score ≥8.25 (BUY): Proceed immediately
3. If score 6.5-8.24 (CONDITIONAL): Ask user for confirmation
4. If score <6.5 (PASS): Reject and explain why
5. Run `open` skill to create position:
   - Calculate position size
   - Create trades/active/TRD-YYYYMMDD-TICKER-ARCH.json
   - Submit entry order
   - Display confirmation

**Use when**: You've already analyzed and scored a ticker (via `/analyze-idea`) and now want to open the position.

**Difference from `/new-trade`**:
- `/new-trade`: Does everything from scratch (screen → analyze → score → open)
- `/open-position`: Opens position from existing scored watchlist item
