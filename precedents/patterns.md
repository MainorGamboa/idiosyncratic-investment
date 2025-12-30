# Named Patterns

Recurring patterns observed across trades. These inform scoring adjustments and kill screens.

---

## 1. Obvious Beneficiary Trap

**Signal:** Company is THE headline legislative winner
**Rule:** -1.5 point penalty (legislative adjustment)
**Examples:** Intel (CHIPS Act), Enphase (IRA)
**Rationale:** Primary beneficiaries often underperform due to being priced in. Market focuses on obvious winners while overlooking secondary beneficiaries.

**Tags:** `obvious_beneficiary`, `legislative`

---

## 2. Macro Conflict

**Signal:** Rate/commodity sensitivity conflicts with legislative thesis
**Rule:** Kill screen (automatic PASS)
**Examples:** ENPH (rate sensitive negated IRA benefits), ALB (lithium price exposure overwhelmed legislative tailwind)
**Rationale:** Macro headwinds overwhelm legislative tailwinds. The legislative catalyst becomes noise when fundamental macro forces dominate.

**Tags:** `macro_conflict`, `legislative`, `kill_screen`

---

## 3. Activist Tier Gap

**Signal:** Tier-1 activist vs Tier-3 activist
**Rule:** Tier-1 = 83% success, +1.0 pts; Tier-2 = 80%, +0.5 pts; Tier-3 = 40% success, +0 pts
**Examples:** Elliott/Starboard (Tier-1) vs first-time activists
**Rationale:** Track record matters significantly in activist campaigns. Tier-1 activists have relationships, capital, and execution capability that dramatically improve odds.

**Tier-1 Activists:** Elliott, Starboard, ValueAct, Pershing Square
**Tier-2 Activists:** Trian, Icahn, Third Point

**Tags:** `activist_tier1`, `activist_tier2`, `activist_tier3`

---

## 4. PDUFA Asymmetry

**Signal:** Rejection moves average 2.7x approval moves
**Rule:** Max position size 1.5% (reduced from 2%)
**Examples:** Biotech FDA binary events
**Rationale:** Downside asymmetry requires smaller sizing despite high base rates (92% post-NDA approval). The 8% tail risk is severe.

**Tags:** `pdufa`, `asymmetric_risk`

---

## 5. Spin-off Timing Pattern

**Signal:** First 5 days post-spin show -2.4% to -3.7% underperformance
**Rule:** Enter on day 30-60 post-spin
**Examples:** Index-driven forced selling creates opportunity
**Rationale:** Institutional rebalancing creates predictable dip. Forced sellers (index funds holding parent) dump spinco shares without regard to value. Window closes as natural buyers emerge.

**Exception:** Immediate S&P 500 inclusion negates pattern

**Tags:** `spinoff`, `timing_pattern`

---

## 6. Third-Party Veto

**Signal:** Merger requires approval from entity with misaligned incentives
**Rule:** -1 point adjustment
**Examples:** Landlord approval, joint venture partner consent, regulatory approval beyond standard HSR
**Rationale:** Additional veto points reduce completion probability. Each third party with veto power introduces orthogonal risk.

**Tags:** `merger_arb`, `third_party_veto`

---

## 7. Breakthrough Therapy + AdCom

**Signal:** FDA breakthrough designation + positive AdCom vote
**Rule:** High conviction setup for PDUFA (base rate >95%)
**Examples:** Breakthrough therapy designations with supporting advisory committee votes
**Rationale:** Combination indicates strong FDA support. Breakthrough designation signals agency enthusiasm; positive AdCom confirms external expert validation.

**Tags:** `pdufa`, `breakthrough_therapy`, `adcom_positive`

---

## Usage Notes

- Patterns are extracted from backtest and real trades
- Each pattern links to specific scoring rules or kill screens
- Tags enable precedent search via `search` skill
- Add new patterns as they emerge from post-mortems
- Update patterns if base rates or rules change

---

*Framework v3.6 | Patterns validated across 40+ trades (2023-2024)*
