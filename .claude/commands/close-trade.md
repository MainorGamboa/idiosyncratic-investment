# Close Trade Command

Expects: trade ID as argument (e.g., /close-trade TRD-20250105-SRPT-PDUFA)

Execute the position closing workflow:

1. Run `close` skill with the trade ID
2. Skill will:
   - Calculate final P&L and return
   - Create post-mortem in trades/closed/wins/ or trades/closed/losses/
   - Update precedents/index.json with tags
   - Archive the trade from trades/active/
3. Display closing summary and lessons learned

Use when exit signal triggers (≥2.0 weighted sum), catalyst occurs, or stop loss hit.
