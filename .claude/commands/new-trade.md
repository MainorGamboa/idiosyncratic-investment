# New Trade Command

Expects: ticker symbol as argument (e.g., /new-trade SRPT)

Execute the COMPLETE workflow from discovery to position opening:

1. Run `screen` skill with the ticker to check kill screens
   - If FAIL: Log to trades/passed/ and STOP
   - If PASS: Continue

2. Run `analyze` skill to create full watchlist file with thesis
   - Creates universe/watchlist/TICKER.md

3. Run `score` skill to complete 6-filter scoring
   - Score <6.5 (PASS): Log to trades/passed/ and STOP
   - Score 6.5-8.24 (CONDITIONAL): Ask user for confirmation
   - Score ≥8.25 (BUY): Auto-proceed to open

4. Run `open` skill to create position:
   - Calculate position size using Kellner Rule + Kelly Fraction
   - Create trades/active/TRD-YYYYMMDD-TICKER-ARCH.json
   - Submit entry order (limit at bid/ask midpoint)
   - Display trade confirmation

5. Display final summary:
   - Trade ID
   - Position size
   - Entry price/order status
   - Exit plan (info parity signals + hard exits)

**This is the end-to-end workflow from idea to open position.**

Use when: You have a ticker and want to go from analysis to position in one command.
