# Schema Changelog

## v1.0 (2025-01-05) - Initial Launch

### Framework Reset
- Reset versioning from v3.7 (pre-release/backtest) to v1.0 (production)
- Formalized technical specification in TECHNICAL_SPEC.md
- Established agent autonomy model and data management protocols

### Features Carried Forward from v3.7
- Market cap ceiling kill screen ($50B base, $100B merger arb, $75B legislative)
- Industry-adjusted Z-Score thresholds (telecom/biotech 1.5, software 2.0, utilities 2.5)
- PDUFA financial health screens (18mo cash runway, D/E <0.75, net cash position)
- 7 archetypes with validated base rates
- 6-filter scoring system (max 11 points)
- Info parity exit protocol (weighted sum thresholds)

### Added (v1.0)
- Data source fallback strategy (IBKR → Stooq → Yahoo)
- Data validation and cross-checking protocols
- Structured logging system (logs/{skill}/YYYY-MM-DD.log)
- Alert system (alerts.json with priority levels)
- Enhanced file organization (wins/losses, trade ID format)
- Order execution logic (limit for entry, market for exits)

### Position Sizing
- Kellner Rule: Max 2% portfolio loss per trade
- Kelly Fraction: 25% negative skew, 50% positive skew
- Archetype caps: Merger 3%, PDUFA 1.5%, Activist 6%, Spinoff 8%, Liquidation 10%, Insider 5%, Legislative 2%

### Known Limitations (v1.0)
- Manual skill invocation (no scheduled automation)
- Single-source data acceptable without cross-check for normal-range metrics
- No portfolio-level correlation detection yet
- No graduated exit thresholds yet (future: 25%/50%/75%/100% scale)
- No multi-catalyst milestone tracking yet

### Future Roadmap (v2.0+)
- Context-aware precedent matching
- Portfolio correlation detection
- Graduated exit thresholds by archetype
- Multi-catalyst milestone tracking
- Automated daily routine (regime → monitor → scan)
