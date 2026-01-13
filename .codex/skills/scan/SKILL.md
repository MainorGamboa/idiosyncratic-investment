---
name: scan
description: Find new catalyst events from external sources like FDA calendar, SEC filings, activist 13Ds. Populates events.json with upcoming catalysts. Use weekly to maintain catalyst calendar or after major news.
---

# Scan Skill

## Purpose
Find new catalyst events from external sources. Populates universe/events.json with upcoming PDUFA dates, merger announcements, activist campaigns, etc.

## When to Use
- Weekly
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

#### Insider Cluster Tracking
**Source:** sec.gov/cgi-bin/browse-edgar (Form 4)

**Look for:**
- Clusters: 3+ insiders buying within 2-week window
- C-suite and board member purchases (CEO, CFO, directors)
- Open market purchases (exclude option exercises, grants)
- Distressed context (stock down >30% from highs)

**Extract:**
- Ticker
- Insider names and titles
- Purchase dates
- Shares purchased
- Purchase prices
- Total cluster value
- Stock context (recent performance)

#### Liquidation / Dissolution
**Sources:**
- SEC Form 8-K (dissolution/liquidation votes)
- SPAC trust discounts (spactrack.net, spachero.com)
- CEF discounts (cefconnect.com)

**Look for:**
- SPACs trading below $10 trust value
- Closed-end funds at discount to NAV >10%
- Corporate liquidation votes or trustee appointments
- Biotech with cash >market cap (liquidation candidates)

**Extract:**
- Ticker
- Type (SPAC, CEF, corporate, biotech)
- NAV or trust value per share
- Current price
- Discount percentage
- Liquidation date or vote date (if announced)

#### Legislative Calendars
**Source:** congress.gov, ballotpedia.org

**Look for:**
- Bill vote schedules (House/Senate floor votes)
- State ballot measures (election dates)
- Regulatory comment period deadlines

**Extract:**
- Bill number or ballot measure name
- Vote date or election date
- Affected sectors/tickers
- Primary vs secondary beneficiaries

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

### Step 4: Write Log Entry

Append to `logs/scan/YYYY-MM-DD.log`:

```json
{
  "timestamp": "2025-01-05T08:00:00Z",
  "skill": "scan",
  "outcome": "COMPLETE",
  "metrics": {
    "new_events_found": 5,
    "sources_checked": ["FDA DAF", "SEC 13D filings", "web search"],
    "events_added": 5
  },
  "data_sources": ["accessdata.fda.gov", "sec.gov"],
  "execution_time_ms": 4200,
  "notes": "Weekly scan completed. 5 new catalyst events added to events.json."
}
```

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

### Insider
- **SEC Form 4 Filings:** sec.gov/cgi-bin/browse-edgar
- **Insider Tracking:** openinsider.com, secform4.com
- **Cluster Filters:** 3+ insiders, 2-week window, open market purchases only

### Liquidation
- **SPAC Trust:** spactrack.net, spachero.com
- **CEF Discounts:** cefconnect.com
- **SEC Form 8-K:** Dissolution/liquidation votes
- **Biotech Cash Screens:** Compare cash per share to market cap

### Legislative
- **Congress.gov:** Bill tracking and vote schedules
- **State Ballot Measures:** ballotpedia.org
- **Regulatory Calendars:** Federal Register for comment periods

## Scan Frequency Recommendations

| Archetype | Frequency | Reason |
|-----------|-----------|--------|
| PDUFA | Weekly | Dates rarely change once set |
| Merger Arb | Daily | Deals announced frequently |
| Activist | Daily | 13D filings can be immediate catalysts |
| Spin-off | Monthly | Long lead times |
| Insider | Daily | Form 4 filings continuous; cluster detection requires monitoring |
| Liquidation | Weekly | SPAC/CEF discounts fluctuate; corporate liquidations less frequent |
| Legislative | Monthly | Bill schedules months in advance |

## Related Skills
- `analyze` — Run on high-priority events
- `screen` — Quick filter after scan identifies new opportunities
- `regime` — Check if regime allows new positions before analyzing events
