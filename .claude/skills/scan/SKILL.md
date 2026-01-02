---
name: scan
description: Find new catalyst events from external sources like FDA calendar, SEC filings, activist 13Ds. Populates events.json with upcoming catalysts. Use weekly to maintain catalyst calendar or after major news.
---

# Scan Skill

## Purpose
Find new catalyst events from external sources. Populates universe/events.json with upcoming PDUFA dates, merger announcements, activist campaigns, etc.

## When to Use
- Weekly (to maintain catalyst calendar)
- After major news (M&A wave, regulatory announcements)
- When exploring new archetype opportunities

## Inputs
```json
{
  "sources": ["fda", "sec", "activist"],
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-06-30"
  },
  "archetypes": ["pdufa", "merger_arb", "activist"]
}
```

**Parameters:**
- `sources` (optional): Which sources to scan (defaults to all)
- `date_range` (optional): Date range to search (defaults to next 6 months)
- `archetypes` (optional): Filter to specific archetypes (defaults to all)

## Process

### Step 1: Scan Each Source

#### FDA Calendar (PDUFA events)
**Source:** accessdata.fda.gov/scripts/cder/daf/index.cfm

**Look for:**
- NDA/BLA submissions with PDUFA dates
- AdCom meeting schedules
- Breakthrough therapy designations
- Fast track designations

**Extract:**
- Application number
- Drug name / company ticker
- PDUFA action date (or AdCom date)
- Indication
- Regulatory pathway

#### SEC Filings (Merger, Activist)
**Source:** sec.gov/edgar/search

**Merger Arb:**
- Search for: "definitive agreement", "merger agreement", "acquisition"
- Form types: 8-K, DEFM14A, SC TO
- Extract: Buyer, target, deal value, expected close date

**Activist:**
- Search for: Schedule 13D filings
- Extract: Filer name, target company, stake %, filing date

#### Spin-off Tracker
**Sources:**
- SEC Form 10 filings
- Company press releases announcing spin-offs
- spinoffresearch.com

**Extract:**
- Parent company
- Spinco name/ticker
- Expected distribution date
- Spin ratio

#### Other Sources
- Liquidation/dissolution notices (SEC Form 8-K)
- Insider cluster tracking (SEC Form 4 filings)
- Legislative calendars (congress.gov for bill votes)

### Step 2: For Each New Event

**Check if Already Exists:**
- Search universe/events.json for ticker + catalyst type
- Skip if duplicate

**Generate Event ID:**
Format: `EVT-{YYYY}-{NNN}`

Find next available number.

**Create Event Object:**
```json
{
  "id": "EVT-2025-042",
  "type": "pdufa",
  "ticker": "SRPT",
  "catalyst": "FDA decision on SRP-9001 for Duchenne muscular dystrophy",
  "date": "2025-02-15",
  "date_type": "hard",
  "archetype": "pdufa",
  "status": "tracking",
  "notes": "Breakthrough therapy designation, positive AdCom vote",
  "linked_idea": null,
  "source": "FDA PDUFA calendar",
  "discovered_date": "2025-01-10"
}
```

### Step 3: Add to Events Calendar
Append new events to `universe/events.json`:

```json
{
  "events": [
    {existing events...},
    {new event 1},
    {new event 2}
  ]
}
```

### Step 4: Prioritize Events
Flag high-priority events for investigation:

**Priority Criteria:**
- PDUFA with breakthrough therapy designation
- Merger spread >5%
- Tier-1 activist 13D filing
- Spin-off from S&P 500 parent

## Output
```json
{
  "sources_scanned": ["fda", "sec"],
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-06-30"
  },
  "new_events": [
    {
      "id": "EVT-2025-042",
      "ticker": "SRPT",
      "type": "pdufa",
      "catalyst": "FDA decision on SRP-9001",
      "date": "2025-02-15",
      "priority": "high"
    },
    {
      "id": "EVT-2025-043",
      "ticker": "ATVI",
      "type": "merger",
      "catalyst": "MSFT acquisition close",
      "date": "2025-03-15",
      "priority": "medium"
    }
  ],
  "events_added": 2,
  "high_priority_count": 1,
  "next_steps": [
    "Run 'analyze' skill on EVT-2025-042 (high priority)",
    "Monitor EVT-2025-043 for spread changes"
  ]
}
```

## Rules
- Always check for duplicates before adding
- Include source URL or reference for verification
- Flag high-priority events for immediate investigation
- Update existing events if status changed (e.g., PDUFA date moved)
- Archive or mark cancelled events (don't delete for historical record)

## Data Sources by Archetype

### PDUFA
- **FDA PDUFA Calendar:** accessdata.fda.gov/scripts/cder/daf
- **FDA AdCom Calendar:** fda.gov/advisory-committees/calendar
- **Biopharmcatalyst:** biopharmcatalyst.com/calendars/pdufa-calendar

### Merger Arb
- **SEC EDGAR:** sec.gov/edgar/search (forms: 8-K, DEFM14A, SC TO)
- **Deal Pipeline:** Various M&A news sources
- **Regulatory Filings:** HSR filings, FTC/DOJ reviews

### Activist
- **SEC 13D Filings:** sec.gov/cgi-bin/browse-edgar (form type: SC 13D)
- **Activist Investor:** 13DMonitor.com
- **Whale Wisdom:** whalewisdom.com

### Spin-off
- **SEC Form 10:** Registration statements for spin-offs
- **Spin-off Research:** spinoffresearch.com
- **Company IR:** Investor relations announcements

### Legislative
- **Congress.gov:** Bill tracking and vote schedules
- **State Ballot Measures:** ballotpedia.org
- **Regulatory Calendars:** Federal Register for comment periods

### Enhanced Activist Sourcing

**Primary Sources**
1. **SEC 13D Filings** — sec.gov/cgi-bin/browse-edgar
   - Form type: SC 13D, SC 13D/A (amendments)
   - Search: Recent filings from past 24 hours
   - Filter: Minimum stake >5% (13D threshold)

2. **13D Monitor** — 13dmonitor.com
   - Tracks all activist campaigns in real-time
   - Pre-filtered by activist tier
   - Includes settlement updates

3. **Activist Insight** — activistinsight.com
   - Campaign tracking and activist fund databases
   - Settlement probabilities

**Secondary Sources (check weekly):**
4. **Whale Wisdom** — whalewisdom.com
   - 13F filings show activist stake building (45-day lag)
   - Useful for pre-13D detection

5. **Hedge Fund 13F Analysis**
   - Track positions of Tier 1/2 activists
   - Look for new concentrated positions (>3% of portfolio)

**Tier-Specific Tracking:**
- **Tier 1** (Elliott, Starboard, ValueAct, Pershing Square): Track ALL filings immediately
- **Tier 2** (Trian, Icahn, Third Point): Track if stake >7.5% or board demands made
- **Tier 3** (Others): Only track if multiple red flags present (turnaround, sale process)

**Event Creation Criteria:**
- 13D filing with stake >5% from Tier 1/2 activist
- 13D amendment announcing board demands or settlement discussions
- Standstill agreement expiration dates (like Elliott/Southwest 2026-04-01)
- Proxy contest announcement (definitive governance catalyst)

**Priority Flags:**
- **High Priority:** Tier-1 activist + stake >10% + explicit demands
- **Medium Priority:** Tier-2 activist + settlement discussions
- **Low Priority:** Tier-3 activist or passive stake increases

## Scan Frequency Recommendations

| Archetype | Frequency | Reason |
|-----------|-----------|--------|
| PDUFA | Weekly | Dates rarely change once set |
| Merger Arb | Daily | Deals announced frequently |
| Activist | **Daily** | **13D filings are immediate catalysts; Tier-1 activists create 10-20% moves** |
| Spin-off | Monthly | Long lead times |
| Legislative | Monthly | Bill schedules months in advance |

## Related Skills
- `analyze` — Run on high-priority events
- `screen` — Quick filter after scan identifies new opportunities
- `regime` — Check if regime allows new positions before analyzing events
