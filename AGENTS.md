# AGENTS.md

## Scope
These guidelines apply to the entire repository.

## Repository Summary
- Python-based catalyst-driven trading system with JSON schemas + Markdown narratives.
- Skills live in `.codex/skills/` and operate on `schema/`, `universe/`, and `trades/` data.
- `schema/*.json` is authoritative; `FRAMEWORK.md` is human-readable context.
- Data and logs are stored in repo (no database).

## Cursor/Copilot Rules
- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` found.

## Common Commands
### Setup
- Install dependencies: `pip install -r requirements.txt`
- IBKR integration requires TWS/Gateway running (defaults in `CONFIG.json`).

### Tests (pytest)
- Run all tests: `pytest`
- Run unit tests only: `pytest tests/unit`
- Run a single test file: `pytest tests/unit/test_position_sizing.py`
- Run a single test class: `pytest tests/unit/test_position_sizing.py::TestKellnerRule`
- Run a single test: `pytest tests/unit/test_position_sizing.py::TestKellnerRule::test_basic_position_sizing`
- Filter by keyword: `pytest -k "position_size"`
- Use markers: `pytest -m unit` (see `pytest.ini` for marker list)

### Lint/Format
- No lint or formatter configured in this repo.
- Keep formatting consistent with existing files (4-space indent, Black-like wrapping).

### Build
- No build step; scripts are executed directly with `python`.

## Project Layout
- `scripts/`: Python modules for data fetching, IBKR integration, sizing, options utils.
- `schema/`: Authoritative rule definitions (kill screens, scoring, exits).
- `universe/`: Events and watchlists (Markdown for narrative, JSON for data).
- `trades/`: Active trades (JSON) and post-mortems (Markdown).
- `tests/`: Pytest suite (unit tests under `tests/unit`).
- `logs/`, `alerts.json`, `alerts_archive.json`: Runtime outputs and alerts.

## Operational Rules (from CLAUDE.md)
- JSON for data, Markdown for narrative.
- Keep structures flat (max two levels of nesting).
- Every decision (including PASS) must be logged under `trades/passed/`.
- `schema/*.json` is the machine-truth; do not edit without explicit user approval.
- Trade IDs use `TRD-YYYYMMDD-TICKER-ARCHETYPE`.

## Decision Thresholds & Risk Controls
- Kill screens are binary; any fail is an immediate PASS.
- Score thresholds: BUY ≥ 8.25, CONDITIONAL 6.5–8.24, PASS < 6.5.
- Kellner Rule caps loss at 2% of portfolio per trade.
- Respect archetype caps (PDUFA 1.5%, Merger 3%, Activist 6%, etc.).
- Exits: info parity weighted sum ≥ 2.0 triggers 50% exit; ≥ 3.0 full exit.
- Ask for confirmation when signals are exact-threshold or high stakes.

## Skills & Commands
- Skills live in `.codex/skills/` and do one thing end-to-end.
- Commands live in `.claude/commands/` and orchestrate multiple skills.
- Typical flow: `scan` → `analyze` → `score` → `open` → `monitor` → `close`.
- Always suggest the next logical skill after completion.
- Do not auto-execute kill-screen overrides or forced exits.

## Code Style Guidelines
### Formatting
- Use 4-space indentation, no tabs.
- Line lengths are typically <= 100 chars (match nearby style).
- Prefer Black-style wrapping for long function signatures.

### Imports
- Order: standard library, third-party, local modules.
- Separate groups with a blank line.
- Use absolute imports within `scripts/` (e.g., `from price_sources import ...`).

### Naming
- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Keep names explicit (avoid 1-letter variables outside very local scopes).

### Types & Data
- Use type hints for public functions and data containers.
- Prefer `dataclasses` for structured records (see `OrderPreview`).
- Return `Optional[...]` when data can be missing and handle gracefully.

### Docstrings
- Modules and public functions use triple-quoted docstrings.
- Keep docstrings concise: purpose + key args/returns.

### Error Handling
- Validate external data before use (range checks, sentinel values).
- Prefer `ValueError` or `RuntimeError` for invalid inputs or critical failures.
- Log warnings/errors to `stderr` when data is unusable.
- Use graceful fallbacks for external data (IBKR → Stooq → Yahoo).

### Testing Conventions
- Tests use `pytest` with classes named `Test*` and functions `test_*`.
- Keep tests deterministic; avoid live network calls.
- Prefer explicit assertions and descriptive failure messages.

### Configuration & Data Files
- Read config from `CONFIG.json`; allow env var overrides when appropriate.
- Never commit credentials; `CONFIG.local.json` is allowed and ignored.
- Avoid mutating `schema/*.json` unless the user explicitly requests it.

## IBKR/External Integrations
- Scripts assume IBKR TWS/Gateway on `127.0.0.1:4002` (paper).
- When adding IBKR operations, always handle timeouts and missing data.
- Treat Greeks/IV data defensively (sentinel values, range checks).

## Data Validation & Fallbacks
- Price data priority: IBKR → Stooq → Yahoo; halt if all fail.
- Cross-check anomalies (>50% daily move, <$0.10 price) across sources.
- Validate M-Score expected range (-2 to +2) and Z-Score range (-5 to +10).
- Strict thresholds: borderline values fail if below thresholds (no tolerance).
- Prefer cached data only for non-critical paths; fetch fresh for monitoring/open/close.

## Logging & Alerts
- Logs live under `logs/<skill>/YYYY-MM-DD.log`.
- Log entries should include timestamp, ticker, outcome, metrics, and sources.
- Alerts are written to `alerts.json`; acknowledged alerts go to `alerts_archive.json`.
- Avoid noisy logs; summarize results and include decision rationale.

## Trade & Universe File Conventions
- Watchlists are Markdown: `universe/watchlist/<TICKER>.md`.
- Active trades are JSON: `trades/active/TRD-YYYYMMDD-TICKER-ARCH.json`.
- Closed trades are Markdown under `trades/closed/wins|losses/`.
- Use snake_case keys in JSON and keep structures shallow (<=2 levels).
- Always log PASS/failed ideas to `trades/passed/` for learning.

## Testing Tips
- Unit tests are preferred for logic (keep them deterministic).
- Mark slow tests with `@pytest.mark.slow` when they take >1s.
- Mark external-service tests with `@pytest.mark.integration`.
- Avoid network calls in unit tests; mock data instead.

## Suggested Workflow for New Features
1. Locate relevant schema or script module in `scripts/`.
2. Update logic with minimal surface-area changes.
3. Add or update unit tests in `tests/unit/` if behavior changes.
4. Run focused pytest commands (single test or file).

## Notes for Agents
- This repo is not a standard Python package; tests adjust `sys.path` to import from `scripts/`.
- Prefer small, targeted edits; avoid reformatting unrelated code.
- When uncertain about business logic, check `FRAMEWORK.md` and `TECHNICAL_SPEC.md`.
