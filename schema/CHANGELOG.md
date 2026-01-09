# Schema Changelog

## v1.1 (2025-01-09) - Archetype-Specific Modifiers Enhancement

### Overview
Enhanced framework with archetype-specific modifiers based on empirical research from Investment 1 & 2. Added new scoring adjustments, kill screens, updated base rates, and expanded data sources.

### New Scoring Modifiers (scoring.json)
- **PDUFA**: Form 483 with OAI (-1.0pt), Prior EMA approval (+0.5pt)
- **Merger Arb**: Second request issued (-1.0pt), China-connected buyer (-1.5pt)
- **Activist**: DSO divergence >20% vs peers (-0.5pt)
- **Spin-off**: WARN filing at SpinCo (position size reduction to 50%, not a score penalty)

### New Kill Screens (kill_screens.json)
- **Insider Cluster Quality (KS-008)**: Requires 3+ opportunistic (non-routine) insiders
  - Routine trader: trades occur in same calendar month annually for 3+ years
  - Eliminates ~50% of false signals by filtering out routine traders
  - Example: Insider sells every June for 3+ years = excluded from cluster count

### Updated Base Rates (archetypes.json)
- **Merger Arb**: post-second request 55-65%, CFIUS-exposed 83%, China-connected 60-70%
- **PDUFA**: AdCom unanimous ~99%, EMA→FDA concordance 91-98%
- Source: Investment 1 & 2 research, empirical regulatory data

### Timeline Adjustments (archetypes.json)
- **Merger Arb**: Second request +90-120 days, CFIUS +160 days
- **PDUFA**: CRL Class 1 resubmission = 2 months (not 6), Class 2 = 6 months

### Regulatory Signals (archetypes.json)
- **PDUFA**: Form 483 with OAI (scoring -1.0), Prior EMA approval (scoring +0.5)
- Rationale: OAI indicates manufacturing violations; EMA concordance validates safety/efficacy

### New Exit Signals (exits.json)
- **Activist**: WARN filing with "loss of contract" language = immediate exit
- Rationale: Major contract loss invalidates activist operational fix thesis

### Operational Risk Signals (archetypes.json)
- **Spin-off**: WARN filing at SpinCo = reduce position size 50%
- Rationale: WARN signals operational distress, warrants risk reduction

### Enhanced Data Sources (CONFIG.json)
- **Regulatory**: openFDA API, FDA FOIA Reading Room, EMA medicines database
- **Insider**: SEC Edgar via EdgarTools, Form 4 historical analysis
- **Activist**: SEC Edgar 13D filings, 13D Monitor (public data)
- **PDUFA**: BioPharmCatalyst, FDA calendar
- **WARN Act**: State databases (California, New York, etc.)

### New Data Fetching Scripts
- `scripts/regulatory_data.py`: FDA Form 483s, EMA approvals, CRL classifications
- `scripts/insider_analysis.py`: Form 4 analysis with routine/opportunistic classification
- `scripts/warn_act_checker.py`: WARN Act database integration

### Cache Policy Updates
- Price: 60 minutes (unchanged)
- Financials: 90 days (unchanged)
- Regulatory: 30 days (new)
- Insider: 7 days (new)

### Skill Updates
- **analyze**: Added insider cluster quality kill screen, WARN filing checks
- **score**: Apply new archetype-specific scoring modifiers
- **monitor**: Check for activist WARN filing exit trigger
- **open**: Apply spin-off position sizing adjustment for WARN filings

### Known Limitations (v1.1)
- Form 483 and EMA approval checks require manual verification (no public API)
- Full Form 4 XML parsing not yet implemented (MVP uses simplified analysis)
- WARN Act database scraping incomplete (manual entry fallback required)
- Some data sources require manual entry until web scraping is implemented

### Future Roadmap (v1.2+)
- Full Form 4 XML parsing for automated insider cluster validation
- WARN Act database scraping automation (state-by-state)
- Enhanced regulatory data integration (Form 483 alerts, EMA auto-lookup)
- DSO divergence calculation from financial data

### Backward Compatibility
- All changes are additive (no breaking changes to v1.0 schema structure)
- Existing trades and watchlist files remain valid
- Skills gracefully degrade when new data sources unavailable

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
