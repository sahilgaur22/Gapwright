# Job Data Sources in Gapwright

*Gapwright: Automated Syllabus-to-Industry Gap Analyzer.*

This document details the architecture, configuration, daily budgets, politeness policies, and compliance rules for all job market data connectors integrated into Gapwright.

---

## 1. Overview and Priority Hierarchy

Gapwright relies on live and benchmark job postings to extract current skill requirements and compare them against university curricula. Sources are organized into tiered priorities to ensure high-relevance geographic matching while respecting API quotas and terms of service.

| Priority | Source | Type | Geographic Focus | Default Daily Budget | Terms & Attribution |
|---|---|---|---|---|---|
| **P1** | **Adzuna** | REST API | **India** (Country: `in`) | ≤ 30 calls/day | Powered by Adzuna; description is excerpt only (`description_is_truncated=True`) |
| **P1** | **Jooble** | REST API (POST) | **India** & Global | ≤ 20 calls/day | Jobs via Jooble; attribution link to `jooble.org` |
| **P2** | **Remotive** | Public JSON | Remote (Worldwide) | ≤ 4 fetches/day | Data from Remotive; **internal skill statistics only** (`may_display_listing=False`) |
| **P2** | **RemoteOK** | Public JSON | Remote (Worldwide) | 1 fetch / 6h | Jobs by RemoteOK; requires regular follow HTML backlink (`may_display_listing=True`) |
| **P2** | **We Work Remotely** | Public RSS | Remote (Worldwide) | 1 fetch / 6h | Jobs via We Work Remotely; plain link back |
| **P3** | **Arbeitnow** | Public JSON | EU & Remote (Off by default) | ≤ 24 calls/day | Jobs by Arbeitnow; client-side filtering |
| **P3** | **HN Who is Hiring** | Algolia HN API | Remote / Global (Off by default) | ≤ 10 calls/day | Hacker News Who is Hiring; monthly thread comments |
| **Demo** | **FixtureSource** | Local JSON | **India** (Bangalore, Hyd, Pune, Mum, Del, Remote) | Unlimited (Offline) | Curated sample dataset; zero network dependency |

---

## 2. Source Connectors

### 2.1 Adzuna (`AdzunaSource`, Priority P1)
- **Endpoint**: `https://api.adzuna.com/v1/api/jobs/{country}/search/{page}`
- **Authentication**: `app_id` and `app_key` via environment variables `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
- **Query Strategy**: Supports `what` (role keyword), `where` (location), `sort_by=date`, and `results_per_page`.
- **Characteristics**: Returns description excerpts only. Postings are flagged with `description_is_truncated = True`.
- **Attribution**: "Powered by Adzuna" linking to `https://www.adzuna.com`.

### 2.2 Jooble (`JoobleSource`, Priority P1)
- **Endpoint**: `https://jooble.org/api/{key}` (HTTP POST)
- **Authentication**: API key via `JOOBLE_API_KEY`.
- **Graceful Degradation**: If `JOOBLE_API_KEY` is absent or unissued, the connector logs a clear warning and disables itself gracefully without raising errors.
- **Attribution**: "Jobs via Jooble" linking to `https://jooble.org`.

### 2.3 Remotive (`RemotiveSource`, Priority P2)
- **Endpoint**: `https://remotive.com/api/remote-jobs`
- **Cadence & Quota**: Strict limit of $\le 4$ fetches/day. Data reflects a ~24-hour publication delay.
- **Terms Constraint**: Remotive API terms permit internal skill demand aggregation but disallow republishing full job listings to third parties. Every `RawJob` sets `may_display_listing = False`.

### 2.4 RemoteOK (`RemoteOKSource`, Priority P2)
- **Endpoint**: `https://remoteok.com/api`
- **Politeness Delay**: Enforces $\ge 500\text{ ms}$ spacing between HTTP calls via domain rate limiting.
- **Preamble Filtering**: RemoteOK returns a legal notice object as the first array element; the connector automatically detects and skips this entry.
- **Backlink Requirement**: Requires a direct follow link (no `rel="nofollow"`) back to RemoteOK.

### 2.5 We Work Remotely RSS (`WeWorkRemotelyRSSSource`, Priority P2)
- **Endpoint**: `https://weworkremotely.com/categories/remote-programming-jobs.rss` and `remote-jobs.rss`
- **Mechanism**: Fetches public XML feeds and parses entries via `feedparser`.
- **Title Parsing**: Dissects standard `"Company: Title"` formats into separate company and role attributes.

### 2.6 Arbeitnow (`ArbeitnowSource`, Priority P3)
- **Endpoint**: `https://www.arbeitnow.com/api/job-board-api`
- **Status**: Disabled by default (`enabled=False`). Enabled only when explicitly included in `ENABLED_SOURCES`.

### 2.7 Hacker News "Who is hiring" (`HNHiringSource`, Priority P3)
- **Endpoint**: Official Algolia search API at `https://hn.algolia.com/api/v1/search_by_date`
- **Status**: Disabled by default. Fetches latest monthly thread comments and parses pipe-delimited metadata (`"Company | Title | Location | Remote"`).

### 2.8 Fixture Source (`FixtureSource`, Priority 10)
- **Data Path**: `backend/app/services/sources/data/indian_jobs_fixture.json`
- **Purpose**: Provides realistic benchmark data for Indian tech hubs (Bangalore, Hyderabad, Pune, Mumbai, Delhi NCR, and India-Remote) across key tech roles (Data Scientist, ML Engineer, Backend Developer, DevOps/SRE, Cloud Architect, etc.).
- **Reliability**: 100% offline, deterministic, zero network latency, used for CI pipelines and offline development.

---

## 3. Configuration and Rate Limiting

### 3.1 Enabling Sources
Active sources are controlled via the `ENABLED_SOURCES` environment variable in `.env`:

```bash
# Default active sources
ENABLED_SOURCES=adzuna,jooble,remotive,remoteok,wwr_rss,fixture

# Offline/CI mode (zero network dependencies)
ENABLED_SOURCES=fixture
```

### 3.2 Token Bucket Rate Limiting
The `DomainRateLimiter` ensures requests to each domain adhere to polite access rates:
- `remoteok.com`: $\ge 500\text{ ms}$ interval
- `remotive.com`: $\ge 250\text{ ms}$ interval
- `weworkremotely.com`: $\ge 250\text{ ms}$ interval
- `api.adzuna.com`: $\ge 100\text{ ms}$ interval

### 3.3 Daily Budgets
Daily usage is tracked in the `api_usage` database table by source and date. Once a source exhausts its daily allocation (`get_remaining_budget() <= 0`), further calls raise `BudgetExhaustedError` and the crawler gracefully falls back to lower-priority sources or fixtures.

---

## 4. Running the Validation Script

The validation script queries enabled connectors to verify connectivity, result volume, date boundaries, and description formatting.

```bash
# Validate all enabled sources against default query (Data Scientist / Bangalore)
python backend/scripts/validate_sources.py

# Validate only the offline fixture dataset
python backend/scripts/validate_sources.py --fixture-only

# Validate specific sources with custom role and location
python backend/scripts/validate_sources.py --sources remotive,remoteok --role "Backend" --limit 5

# Run in CI without failing on unconfigured P1 API keys
python backend/scripts/validate_sources.py --no-require-p1
```

### Sample Validation Output

```
Starting Gapwright Job Source Validation...
Role: 'Data Scientist' | Location: 'Bangalore' | Limit: 10

======================================================================================
Source     | Tier | Status | Count | Median Len | % Trunc | Sample Titles                   
--------------------------------------------------------------------------------------
adzuna     | P1   | OK     | 2     | 185 chars  | 100.0%  | Lead Data Scientist, ...        
fixture    | P10  | OK     | 1     | 266 chars  | 0.0%    | Lead Data Scientist             
======================================================================================

[VALIDATION SUCCESS] Enabled sources validated successfully.
```
