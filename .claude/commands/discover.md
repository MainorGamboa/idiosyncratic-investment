# Discover New Opportunities Command

Execute catalyst discovery workflow to find new trade ideas:

1. Run `scan` skill to find new catalyst events from external sources:
   - FDA PDUFA calendar (accessdata.fda.gov)
   - SEC 13D filings (activist campaigns)
   - Merger announcements (SEC 8-K filings)
   - Spin-off announcements
   - Legislative developments
2. Update universe/events.json with upcoming catalysts
3. Display newly discovered events by archetype
4. For each new event, ask if user wants to analyze the ticker using `/analyze-idea TICKER`

This should be run weekly to maintain an active catalyst calendar with 8-12 tracked events.

**Goal**: Maintain 8-12 active catalyst events across all archetypes.
