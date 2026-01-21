Merger Arb Second Request in Lina Khan FTC Era

Research Question: Has the FTC Second Request abandonment rate changed under Lina Khan 
(2021-present) compared to prior periods, and by industry/deal characteristics?

Dataset Required:
- All merger deals 2017-2025 that received Second Requests
- Include: Acquirer, target, industry, deal size, deal structure (cash/stock), filing date, 
  Second Request date, outcome (approved/abandoned), outcome date
- Segment by era: Pre-Khan (2017-June 2021) vs Khan Era (July 2021-present)

Data Sources:
- FTC Press Releases (ftc.gov/news-events)
- DOJ Press Releases (justice.gov/atr)
- SEC EDGAR (merger proxy statements, 8-K filings for Second Request disclosure)
- Merger deal databases (if accessible): Capital IQ, PitchBook, or manual compilation

Analysis Required:
1. Calculate abandonment rate by era:
   - Pre-Khan: % of Second Request deals abandoned
   - Khan Era: % of Second Request deals abandoned
2. Segment by industry: Tech, pharma/healthcare, industrial, consumer, financial
3. Segment by deal size: <$1B, $1-5B, $5-20B, >$20B
4. Segment by market concentration: HHI increase (if available), or proxy via market share
5. Calculate average timeline: Second Request to resolution (days)

Hypothesis Tests:
- H1: Khan Era has higher abandonment rate than Pre-Khan
- H2: Tech deals face higher scrutiny (higher abandonment rate)
- H3: Larger deals (>$5B) face longer timelines

Output Required:
- Updated base rate: Post-Second Request success rate (currently framework shows 55-65%)
- Industry-specific adjustments: "If tech deal + Second Request → additional -X adjustment"
- Timeline update: Expected days to resolution by era and industry
- Scoring recommendation: Update current -1.0 adjustment for Second Request (increase 
  penalty if abandonment rate rose)

Success Criteria:
- Clear comparison Pre-Khan vs Khan Era
- Industry-specific risk quantified
- Updated framework scoring reflects current regulatory reality


Spin-Off Entry Window Validation
Research Question: Empirically test optimal entry window for spin-off trades. Framework 
claims days 30-60 post-spin are optimal. Validate with data.

Dataset Required:
- All spin-offs 2018-2025 (US-listed companies)
- Parent company, SpinCo, spin date, Form 10 filing date
- SpinCo price data: Daily prices from T (spin date) to T+180 days
- Index inclusion: Was SpinCo included in S&P 500, Russell 2000, etc.?
- Market cap, sector, debt allocation (% of combined debt allocated to SpinCo)

Data Sources:
- Spin-off database: Manual compilation from 8-K filings (SEC EDGAR)
- Form 10 filings (SEC EDGAR)
- Price data: Yahoo Finance, Stooq
- Index inclusion: S&P, Russell index changes announcements

Analysis Required:
1. Calculate forward returns for different entry windows:
   - Entry at T+0 to T+7 (immediate post-spin)
   - Entry at T+8 to T+29
   - Entry at T+30 to T+60 (framework recommendation)
   - Entry at T+61 to T+90
   - Entry at T+91 to T+180
2. Measure returns: From entry to T+180, T+365 (6-month and 1-year forward)
3. Control variables:
   - Market cap: Small (<$1B) vs mid ($1-10B) vs large (>$10B)
   - Index inclusion: Included vs excluded
   - Sector: Does industry matter?
   - Debt allocation: High debt (>50% of combined) vs low debt

Hypothesis Tests:
- H1: Entry at T+30-60 produces higher forward returns than T+0-7 (forced selling hypothesis)
- H2: Small-cap spin-offs without index inclusion have stronger T+30-60 entry effect
- H3: Volume pattern predicts optimal entry (volume decline to <1.5x 20-day average)

Volume Pattern Analysis:
- For each spin-off, identify day when volume drops to <1.5x 20-day average AND price 
  stabilizes (<2% daily moves)
- Test: Does entering on this signal produce better returns than fixed T+30-60 window?

Output Required:
- Table: Entry window vs forward returns (6mo, 12mo) by market cap and index inclusion
- Recommendation: Confirm or adjust optimal entry window
- Volume signal validation: Does waiting for volume decline improve returns?
- Edge cases: When should you enter immediately? (S&P 500 inclusion, etc.)

Success Criteria:
- Clear empirical evidence for T+30-60 window OR new optimal window identified
- Volume signal validated or rejected
- Confidence in entry timing recommendations


Therapeutic Area Success Rates - Validation
Research Question: Validate therapeutic area Likelihood of Approval (LOA) rates currently 
in framework (Hematology 26%, Rare Disease 25%, CNS 8%, Solid Tumor 4%) with 2020-2025 data.

Dataset Required:
- All FDA NDA/BLA submissions 2020-2025
- Drug name, company, therapeutic area, indication, submission date, PDUFA date, outcome 
  (approved/CRL), CRL reason (if applicable)
- Study design: RCT vs single-arm, primary endpoint type, surrogate vs clinical endpoint

Data Sources:
- FDA CDER (Center for Drug Evaluation and Research) database
- FDA Drug Approvals and Databases (accessdata.fda.gov/scripts/cder/daf/)
- BioPharma Catalyst (PDUFA calendar with outcomes)
- ClinicalTrials.gov (study design details)

Therapeutic Areas to Analyze:
- Hematology / Blood Disorders
- Rare Disease / Orphan Drugs
- Infectious Disease
- CNS / Neurology
- Oncology (all)
- Oncology - Solid Tumor (subset)
- Oncology - Hematologic (subset)
- Cardiovascular
- Metabolic / Endocrine

Analysis Required:
1. Calculate LOA by therapeutic area: (Approvals / Total submissions)
2. Segment by study design:
   - Single-arm vs RCT
   - Surrogate endpoint vs clinical endpoint
   - Accelerated approval vs standard
3. Segment by drug type: Small molecule vs biologic vs gene therapy vs cell therapy
4. Calculate post-CRL success rate by therapeutic area and CRL reason:
   - CMC-only CRL: X% approval on resubmission
   - Efficacy CRL: Y% approval on resubmission
   - Safety CRL: Z% approval on resubmission

Hypothesis Tests:
- H1: Rare disease LOA remains ~25% (framework assumption)
- H2: Gene therapies have different LOA than small molecules within same therapeutic area
- H3: Surrogate endpoints have lower LOA than clinical endpoints (harder FDA approval)

Output Required:
- Updated LOA table by therapeutic area (2020-2025 data)
- Study design adjustments: "Single-arm study in oncology → reduce Catalyst score by X"
- Post-CRL success rates by therapeutic area and CRL type
- Recommendation: Update framework archetypes.json therapeutic_area_loa section

Success Criteria:
- LOA rates validated or corrected with recent data
- Study design risk quantified (scoring adjustments)
- Confidence in Catalyst scoring (2.0 points) based on therapeutic area


Form 483 / OAI Severity Index
Research Question: Create a severity index for FDA Form 483 observations and Official Action 
Indicated (OAI) classifications to enable graduated scoring adjustments (not binary -1.0).

Dataset Required:
- All FDA Form 483s issued 2018-2025 (focus on drug manufacturing sites)
- Include: Company, site, inspection date, observations (text), classification (NAI/VAI/OAI), 
  subsequent PDUFA outcome
- Match Form 483s to PDUFA outcomes: Did the drug get approved despite 483? Delayed? CRL?

Data Sources:
- FDA FOIA (Freedom of Information Act) Reading Room (fda.gov/regulatory-information/
  freedom-information)
- FDA Warning Letters database (accessdata.fda.gov/scripts/warningletters/)
- FDA Inspection Classifications (fda.gov/inspections-compliance-enforcement-and-criminal-
  investigations/inspection-classification-database)

Analysis Required:
1. Classify Form 483 observations by severity:
   - Category A (Low): Documentation issues, labeling errors, minor GMP deviations
   - Category B (Medium): Process deviations, testing failures, validation gaps
   - Category C (High): Contamination, data integrity issues, repeated failures
   - Category D (Critical): Falsification, patient safety risk, systemic failures

2. Calculate PDUFA outcome by 483 severity:
   - Category A: X% approval rate
   - Category B: Y% approval rate
   - Category C: Z% approval rate
   - Category D: W% approval rate

3. OAI analysis:
   - OAI with no Form 483: Approval rate?
   - OAI with Category A-B 483: Approval rate?
   - OAI with Category C-D 483: Approval rate?

4. Timeline impact:
   - Does a Form 483 delay PDUFA? By how many days on average by category?

Output Required:
- Form 483 Severity Index: 4-category classification with definitions
- Scoring adjustments by severity:
  - Category A: -0.25 (minor risk)
  - Category B: -0.5 (moderate risk)
  - Category C: -1.0 (current framework default)
  - Category D: -2.0 or KILL SCREEN (critical risk)
- Decision tree: "Form 483 + OAI + Category X → Adjustment Y"
- Update schema/archetypes.json and schema/scoring.json

Success Criteria:
- Clear severity classification criteria (not subjective)
- Graduated adjustments replace binary -1.0
- Can be applied programmatically (keyword matching in 483 text)


DSO Divergence as Operational Difficulty Proxy
Research Question: Is DSO (Days Sales Outstanding) divergence the best metric for assessing 
activist operational fix difficulty, or are there better alternatives? Optimize the 
operational difficulty scoring.

Dataset Required:
- All activist campaigns 2018-2025 with operational improvement thesis (not just M&A)
- Target company, activist, campaign start date, outcome, stock return (entry to settlement, 
  entry to T+12mo)
- Financial metrics at campaign start:
  - DSO vs peer average (divergence %)
  - Inventory turns vs peer average
  - SG&A as % of revenue vs peer average
  - ROIC vs peer average
  - Gross margin vs peer average
  - Operating margin vs peer average

Data Sources:
- 13D filings (SEC EDGAR)
- Activist campaign databases (13D Monitor, Activist Insight, or manual compilation)
- Financial data: Capital IQ, Bloomberg, Koyfin, or manual from 10-K/10-Q

Peer Group Definition:
- For each target, identify 5-10 peers (same industry, similar size)
- Calculate peer average for each metric
- Calculate divergence: (Company metric - Peer avg) / Peer avg

Analysis Required:
1. Test correlation: Which metric best predicts activist success?
   - DSO divergence vs success rate
   - Inventory turns divergence vs success rate
   - SG&A divergence vs success rate
   - ROIC spread vs success rate
   - Gross margin divergence vs success rate

2. Multivariate model:
   - Create "Operational Fix Difficulty Score" combining multiple metrics
   - Use logistic regression or decision tree to weight factors
   - Output: Probability of activist success given operational metrics

3. Threshold identification:
   - Current framework: DSO divergence >20% → -0.5 adjustment
   - Test alternatives: >15%, >25%, >30%
   - Test combinations: "DSO divergence >20% AND ROIC spread >500bp → -1.0 adjustment"

Hypothesis Tests:
- H1: DSO divergence >20% predicts lower activist success rate
- H2: Multiple metrics combined predict better than DSO alone
- H3: Some divergences are easier to fix (SG&A) vs harder (ROIC)

Output Required:
- Best predictor identified: DSO, SG&A, ROIC, or combination
- Updated scoring adjustment formula
- Decision tree: "If DSO divergence >X% and ROIC spread >Y bp → adjustment -Z"
- Update schema/scoring.json activist adjustments

Success Criteria:
- Predictor(s) have statistically significant correlation with outcomes
- New formula outperforms current DSO-only approach
- Can be calculated programmatically from financial data

Merger Spread Minimum - Industry Specific
Research Question: Is the 2.5% merger spread kill screen appropriate across all industries 
and deal types, or should it vary? What is the optimal minimum spread for risk-adjusted returns?

Dataset Required:
- All cash merger deals 2018-2025 with spread data
- Acquirer, target, industry, deal size, deal structure, announcement date, expected close 
  date, actual close date (or abandonment date)
- Spread data: Spread at announcement, spread 30 days post-announcement, spread at close
- Outcome: Completed vs abandoned

Data Sources:
- Merger deal databases: Manual compilation from 8-K filings, press releases
- Spread data: Historical stock prices vs deal price (calculate spread)
- Deal outcomes: SEC filings (completion 8-K or termination 8-K)

Deal Segmentation:
- By industry: Tech, pharma/healthcare, financial, industrial, consumer, energy
- By deal size: <$1B, $1-5B, $5-20B, >$20B
- By buyer type: Strategic vs private equity
- By structure: All-cash vs cash-and-stock (focus on all-cash for spread clarity)
- By market cap: Large-cap target (>$10B) vs mid-cap ($2-10B) vs small-cap (<$2B)

Analysis Required:
1. Calculate completion rate by spread at T+30 days:
   - Spread <2%: X% completion rate
   - Spread 2-2.5%: Y% completion rate
   - Spread 2.5-5%: Z% completion rate
   - Spread >5%: W% completion rate

2. Calculate annualized returns by spread:
   - Spread <2%: (Spread / Days to close * 365) = A% annualized
   - Repeat for each cohort
   - Measure: Risk-adjusted return (return / abandonment risk)

3. Industry analysis:
   - Tech deals: Average spread, completion rate
   - Pharma deals: Average spread, completion rate
   - Compare across industries

4. Test hypothesis:
   - H1: Spreads <2.5% in low-risk industries (utilities, industrials) still have high 
     completion rates
   - H2: Spreads <2.5% in high-risk industries (tech, pharma) signal deal risk
   - H3: PE buyers have tighter spreads than strategic buyers (financing risk)

Output Required:
- Industry-specific spread minimums:
  - Utilities/Industrials: May allow <2.5% (e.g., 2.0%)
  - Tech/Pharma: Keep 2.5% or increase to 3.0%
- Deal type adjustments: Strategic buyer vs PE buyer vs foreign buyer
- Risk-adjusted optimal spread: "Target spreads offering ≥20% annualized with <10% 
  abandonment risk"
- Update schema/kill_screens.json merger_spread thresholds

Success Criteria:
- Evidence that 2.5% threshold is too strict or too lenient for certain industries
- Optimal spread identified by industry and deal type
- Framework captures best risk-adjusted merger arb opportunities


Cockroach Rule Taxonomy
Research Question: Validate the "cockroach rule" (first bad news predicts more bad news) 
and create a severity taxonomy for graduated responses instead of automatic exit.

Dataset Required:
- Historical trades 2018-2025 across all archetypes with "cockroach" events
- Define cockroaches:
  - PDUFA: FDA delay, AdCom negative, manufacturing issue, CRL
  - Merger: Financing delay, regulatory delay, board dissent, third-party bid
  - Activist: Activist reduces stake, company rejects demands, proxy fight loss
  - Spin-off: Spin date delay, debt allocation change, WARN filing
  - Insider: Insider sells, company misses earnings, accounting issue

- For each cockroach: Event date, stock price at event, subsequent events (more cockroaches?), 
  final outcome (win/loss), return if exited at first cockroach vs held

Data Sources:
- Your closed trades + passed trades with notes
- Public sources: 8-K filings, press releases, FDA announcements
- Price data: Yahoo Finance

Analysis Required:
1. Cockroach probability model:
   - Given first cockroach, what % chance of second cockroach?
   - Given second cockroach, what % chance of third?
   - By archetype: Do PDUFA cockroaches predict differently than merger cockroaches?

2. Severity classification:
   - Minor cockroach: Example - FDA requests minor clarification, activist reduces stake 
     from 9% to 8%
   - Moderate cockroach: Example - Merger spread widens 200bp, activist loses proxy vote 
     but stays engaged
   - Major cockroach: Example - FDA issues CRL, merger Second Request issued, activist exits 
     entirely

3. Outcome analysis by response:
   - Exit on first minor cockroach: Average return vs buy-and-hold
   - Exit on first moderate cockroach: Average return vs buy-and-hold
   - Exit on first major cockroach: Average return vs buy-and-hold

4. False positives:
   - How often does first cockroach NOT lead to subsequent bad news?
   - What characteristics predict false positives?

Hypothesis Tests:
- H1: First cockroach predicts >50% chance of second cockroach (validates rule)
- H2: Major cockroaches have >75% chance of subsequent bad news (always exit)
- H3: Minor cockroaches have <30% chance of subsequent bad news (don't exit automatically)

Output Required:
- Cockroach Severity Taxonomy:
  - Minor: Monitor closely, tighten stop loss, no immediate exit
  - Moderate: Exit 50% of position, reassess thesis
  - Major: Exit 100% immediately (current rule)
- Archetype-specific cockroach definitions
- Decision tree: "Cockroach type X in archetype Y → action Z"
- Update schema/exits.json cockroach_rule section

Success Criteria:
- Empirical validation that first cockroach predicts more bad news
- Graduated response system replaces binary exit rule
- Framework avoids exiting on false positives while capturing true risk signals
