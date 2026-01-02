# IDIOSYNCRATIC TRADING FRAMEWORK v3.7

*Catalyst-Driven Special Situations | 7 Archetypes | Backtest-Validated*

---

## Decision Flow

```
KILL SCREENS → SCORE (6 Filters) → SIZE → ENTER → MONITOR → EXIT
```

**Thresholds:** BUY ≥8.25 | CONDITIONAL 6.5-8.24 | PASS <6.5

---

## 1. Kill Screens

Binary gates. Any fail = automatic PASS.

| Screen | Fail Condition | Applies To |
|--------|----------------|------------|
| Beneish M-Score | > -1.78 | All |
| Altman Z-Score | < threshold (industry-adjusted) | All |
| **Market Cap Ceiling** | **> $50B (base), $100B (merger), $75B (legislative)** | **All** |
| Hostile Deal | Yes | Merger Arb |
| Merger Spread | < 2.5% | Merger Arb |
| Macro Conflict | Rate/commodity conflicts | Legislative |
| **PDUFA Financial Health** | **Cash runway <18mo, D/E >0.75, or net debt** | **PDUFA** |

### Industry-Specific Z-Score Adjustments

The Altman Z-Score was designed for manufacturing companies. Adjust thresholds by sector:

| Industry | Threshold | Rationale |
|----------|-----------|-----------|
| Manufacturing (default) | 1.81 | Original Altman formula |
| Telecom/Media | 1.5 | Asset-light, negative working capital by design |
| Biotech/Pharma | 1.5 | R&D-heavy, evaluate cash runway separately |
| Software/SaaS | 2.0 | Negative working capital normal (deferred revenue) |
| Utilities | 2.5 | High leverage normal due to regulated cash flows |
| Financials/Banks | N/A | Use Tier 1 Capital Ratio, NPL ratio instead |

**Validation Required:** When using adjusted threshold, confirm with secondary metrics (Piotroski F-Score, interest coverage, cash position).

---

## 2. Scoring (11 Points Max)

| Filter | Max | Question |
|--------|-----|----------|
| Catalyst | 2 | Defined event with known timeline? |
| Mispricing | 2 | Gap between price and fair value? |
| Noise Survival | 2 | Can survive volatility until catalyst? |
| Downside Floor | 2 | Asset value if thesis fails? |
| Risk/Reward | 2 | 3:1 = 2pts, 2:1 = 1pt |
| Info Half-Life | 1 | Edge persists through catalyst? |

### Adjustments

**Activist:** +1.0 Tier-1, +0.5 Tier-2  
**Legislative:** -1.5 obvious beneficiary, -1.0 macro-sensitive  
**Merger:** -1 third-party veto, -2 DOJ/FTC lawsuit

---

## 3. Archetypes

| Archetype | Key Base Rate | Max Size | Entry Timing |
|-----------|---------------|----------|--------------|
| Merger Arb | 94% friendly | 3% | Immediate |
| PDUFA | 92% post-NDA | 1.5% | Pre-catalyst |
| Activist | 83% Tier-1 | 6% | On 13D |
| Spin-off | Year 2 peak | 8% | 30-60 days post |
| Liquidation | 99% SPAC | 10% | At discount |
| Insider | 65-70% cluster | 5% | On cluster |
| Legislative | Low (primary) | 2% | 3-6 mo pre |

---

## 4. Position Sizing

**Kellner Rule:** Max 2% portfolio loss per trade

| Skew | Kelly | Archetypes |
|------|-------|------------|
| Negative | 25% | Merger, PDUFA, Activist |
| Positive | 50% | Spin-off, Liquidation |

---

## 5. Exit Protocol

### Info Parity Signals
- **Media:** 2+ mainstream articles
- **IV:** Options IV > 2x average  
- **Price:** >50% move toward target

**Logic:** weighted_sum < 2 → Watch | ≥ 2 → Exit 50% | ≥ 3 → Full exit

### Hard Exits
- **Cockroach Rule:** First regulatory delay, financing wobble, or board dissent → EXIT
- **Finerman Corollary:** Deal breaks → Sell first, revisit later
- **200-day MA:** Below MA → Defensive posture
- **Thesis Break:** Core thesis invalidated → EXIT

---

## 6. Regime Overlays

| Condition | Action |
|-----------|--------|
| VIX > 30 sustained | Pause all new merger arb |
| VIX 20-30 | Reduce risk, widen stops |
| HY OAS widens 100bp+ | Reduce merger arb proportionally |

---

## 7. Named Patterns

| Pattern | Signal | Rule |
|---------|--------|------|
| Obvious Beneficiary | Headline legislative winner | -1.5 penalty |
| Macro Conflict | Rate/commodity sensitivity | Kill screen |
| Activist Tier Gap | Tier-1 = 83%, Tier-3 = 40% | Tier bonus |
| PDUFA Asymmetry | Rejection moves 2.7x approval | 1.5% cap |
| Spin-off Timing | First 5 days = -2.4% to -3.7% | Enter day 30-60 |

---

## 8. Backtest Validation (2023-2024)

| Tier | Win Rate | Avg Return |
|------|----------|------------|
| BUY (≥8.25) | 68% | +18.4% |
| CONDITIONAL | 55% | +8.2% |
| PASS (<6.5) | 29% | -15.0% |

**Sharpe:** 1.4-1.8

---

## Quick Reference

```
KILL SCREENS:
  M-Score > -1.78 → PASS
  Z-Score < 1.81 → PASS
  Hostile → PASS
  Spread < 2.5% → PASS
  Macro Conflict → PASS

SCORING (11 max):
  Catalyst (2) + Mispricing (2) + Noise (2) + 
  Floor (2) + R/R (2) + Info Half-Life (1)

DECISION:
  ≥ 8.25 → BUY
  6.5-8.24 → CONDITIONAL
  < 6.5 → PASS

SIZING:
  Never exceed archetype cap
  Max loss 2% per trade (Kellner)
  Quarter-Kelly for negative skew
  Half-Kelly for positive skew

EXIT:
  Info parity ≥ 2 → Exit 50%
  Info parity ≥ 3 → Full exit
  Cockroach → Exit immediately
  Thesis break → Exit regardless of price
```

---

*Framework v3.6 | December 2024 | Backtest-Validated (40+ trades, p < 0.10)*
