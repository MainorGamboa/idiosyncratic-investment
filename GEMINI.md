# Gemini Context: Idiosyncratic Trading System

This `GEMINI.md` provides the context and operational guidelines for Gemini when interacting with this Idiosyncratic Trading System.

## 1. Project Overview

This project is an **agentic trading system** implementing a catalyst-driven special situations framework. It automates the analysis, scoring, and execution of trades across 7 specific archetypes:
*   Merger Arbitrage
*   PDUFA (FDA Approvals)
*   Activist
*   Spin-off
*   Liquidation
*   Insider
*   Legislative

The system follows a strict decision pipeline:
`KILL SCREENS → SCORE (6 Filters) → SIZE → ENTER → MONITOR → EXIT`

## 2. Architecture & Data Structure

The system separates **data (JSON)** from **narrative (Markdown)**.

### Key Directories
*   **`schema/`**: Machine-readable rules. **Authoritative.**
    *   `archetypes.json`, `kill_screens.json`, `scoring.json`, `exits.json`.
*   **`universe/`**: The idea pipeline.
    *   `events.json`: Calendar of catalysts.
    *   `watchlist/`: Active investigations (`TICKER.md`).
    *   `screened/`: Logs of kill screen results.
*   **`trades/`**: Decision traces.
    *   `active/`: JSON files for open positions (`TRD-YYYYMMDD-TICKER-ARCH.json`).
    *   `closed/`: Markdown post-mortems for wins/losses.
    *   `passed/`: JSON logs for ideas that failed kill screens or scoring.
*   **`precedents/`**: Pattern library (`index.json`, `patterns.md`).
*   **`scripts/`**: Python integration scripts (`ibkr_paper.py`).

### Key Files
*   **`FRAMEWORK.md`**: Human-readable investment logic.
*   **`TECHNICAL_SPEC.md`**: Detailed technical implementation and agent behavior.
*   **`CLAUDE.md`**: Operational guidelines (primary reference for agent behavior).
*   **`CONFIG.json`**: System state, account size, risk parameters.

## 3. Operational Skills (Gemini's Role)

You will act as the operator of this system, performing "Skills" as defined in `CLAUDE.md`.

| Skill | Action | Key Files/Schemas to Reference |
| :--- | :--- | :--- |
| **`regime`** | Update `CONFIG.json` with VIX/Credit spreads. | `CONFIG.json` |
| **`screen`** | Run kill screens (binary pass/fail). | `schema/kill_screens.json` |
| **`analyze`** | Full analysis: kill screens → watchlist creation. | `schema/kill_screens.json`, `universe/watchlist/` |
| **`score`** | Complete 6-filter scoring (max 11 pts). | `schema/scoring.json`, `universe/watchlist/` |
| **`open`** | Open position (sizing, trade file creation). | `schema/archetypes.json`, `trades/active/` |
| **`monitor`** | Check active trades for exit signals. | `schema/exits.json`, `trades/active/`, `alerts.json` |
| **`close`** | Close position & create post-mortem. | `trades/active/` → `trades/closed/`, `precedents/` |
| **`scan`** | Find new catalysts. | `universe/events.json` |
| **`search`** | Find precedents. | `precedents/index.json` |

## 4. Workflows & Conventions

### Trade ID Format
`TRD-YYYYMMDD-TICKER-ARCHETYPE` (e.g., `TRD-20250105-SRPT-PDUFA`)

### Decision Making
1.  **Kill Screens:** STRICT enforcement. M-Score > -1.78 is a PASS. Market Cap > limit is a PASS.
2.  **Scoring:**
    *   **BUY (≥8.25):** 68% hist. win rate.
    *   **CONDITIONAL (6.5-8.24):** Requires user confirmation.
    *   **PASS (<6.5):** Log to `trades/passed/`.
3.  **Position Sizing:** Min of (Kelly Fraction, Archetype Cap, Kellner Rule).
4.  **Exits:**
    *   **Hard Exits:** Cockroach Rule, Thesis Break (Exit immediately).
    *   **Info Parity:** Weighted sum of Media, IV, Price. ≥2.0 (50% exit), ≥3.0 (Full exit).

### Data Handling
*   **Price:** IBKR (Paper) > Stooq > Yahoo.
*   **Financials:** SEC API > Manual.
*   **Validation:** Cross-check price anomalies (>50%) or extreme metrics.

### IBKR Integration
Use `python scripts/ibkr_paper.py` for execution if requested.
*   `python scripts/ibkr_paper.py place Ticker BUY Shares ...`
*   `python scripts/ibkr_paper.py positions`

## 5. Agent Instructions

*   **Be "Ask-First":** If a kill screen is ambiguous or a metric is borderline, ask the user.
*   **Log Everything:** Every decision (even a PASS) generates a file.
*   **Context Aware:** When scoring, check `precedents/` for similar past trades.
*   **Markdown for Humans, JSON for Machines:** Ensure `trades/*.json` files are strictly valid JSON and `universe/watchlist/*.md` files are descriptive.
