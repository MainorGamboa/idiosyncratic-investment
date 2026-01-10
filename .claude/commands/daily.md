# Daily Autonomous Trading Cycle

Execute the complete autonomous daily trading workflow:

## Full Cycle (No User Intervention Required)

1. **Update Regime** (`regime` skill)
   - Check VIX, credit spreads
   - Update CONFIG.json
   - Set market conditions

2. **Monitor Existing Positions** (`monitor` skill)
   - Check all active trades for exit signals
   - If exit signal ≥2.0: Auto-close position (`close` skill)
   - Create post-mortems for closed trades

3. **Discover New Events** (`scan` skill)
   - Scan FDA PDUFA calendar
   - Scan SEC 13D filings (activists)
   - Find merger announcements
   - Update universe/events.json

4. **Process Events Pipeline**
   - For each event WITHOUT watchlist file:
     - Run `screen` → If PASS: Run `analyze` → Run `score`
     - If score ≥8.25 (BUY): Auto-open position (respects max_positions limit)
     - If score 6.5-8.24 (CONDITIONAL): Log to trades/conditional/
     - If score <6.5 (PASS): Log to trades/passed/

5. **Daily Summary**
   - Regime state
   - Positions opened today
   - Positions closed today
   - Active positions count
   - New events discovered
   - Alerts requiring attention

Max positions limit (from CONFIG.json) prevents overtrading.

