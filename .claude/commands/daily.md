# Daily Routine Command

Execute the standard morning routine for the trading system:

1. Run the `regime` skill to update VIX, credit spreads, and market conditions in CONFIG.json
2. Run the `monitor` skill to check all active trades for exit signals
3. Display any active alerts from alerts.json
4. Provide a brief summary of regime state and any action items

This should be run every market day before 9:30 AM ET.
