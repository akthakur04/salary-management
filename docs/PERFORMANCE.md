# Performance

**Budget** (REQUIREMENTS §6, ARCHITECTURE §6): p95 under **300 ms** for the list and insight endpoints, with 10,000 employees and their compensation history.

**Result: every budgeted endpoint is within it.** The directory and profile endpoints answer in 2–22 ms (p95). The insight endpoints are at about 230–260 ms, so they're the ones to watch.

## How it was measured

```bash
cd backend
alembic upgrade head
python -m app.seed
python scripts/time_endpoints.py --runs 30
```

- **Data:** the full seed (10,000 employees, 26,776 compensation versions, 32,249 components), as of 12 Nov 2026.
- **What's timed:** requests go through the whole app in-process (routing, the session check, validation, the database, the domain calculations and serialisation), but not over a network. The numbers are server time. Each endpoint gets 3 warm-up requests, then 30 timed ones.
- **Environment:** SQLite 3.49 on an Apple M4 laptop, Python 3.12, measured 14 Nov 2026. Postgres on Render will differ. These results show the design meets the budget at this scale; they aren't a production benchmark.

## Results

| Endpoint | p50 (ms) | p95 (ms) | max (ms) | Within 300 ms |
|---|---:|---:|---:|:---:|
| Directory, first page | 12 | 14 | 22 | yes |
| Directory, India + Engineering | 9 | 17 | 27 | yes |
| Directory, sorted by total pay (USD) | 21 | 22 | 22 | yes |
| Directory, below band | 18 | 19 | 35 | yes |
| Directory, name search | 10 | 11 | 11 | yes |
| Profile | 9 | 10 | 29 | yes |
| Compensation history | 2 | 2 | 2 | yes |
| Insights summary | 219 | 239 | 246 | yes |
| Breakdown by country | 216 | 234 | 240 | yes |
| Breakdown by department | 220 | 239 | 268 | yes |
| Breakdown by level | 220 | 235 | 246 | yes |
| Band distribution | 216 | 231 | 233 | yes |
| Exceptions, below band | 222 | 261 | 333 | yes |
| Exceptions, due soon | 223 | 238 | 249 | yes |
| Recent changes | 6 | 6 | 6 | yes |
| CSV export, all employees (not in the budget) | 241 | 260 | 281 | n/a |

## What makes it fast

| Technique | Where |
|---|---|
| Server-side paging (max 100 rows), sorting and filtering, all in one indexed SQL query | `EmployeeRepository.search` |
| Each version stores its local-currency totals, so no query unpacks components | `compensation_version.fixed_cash_minor` / `target_variable_minor` / `ttc_minor` |
| Indexes on the "version in force" lookup, role, country, status and name, plus a partial unique index for open versions | ARCHITECTURE §4 |
| Band position is filtered in SQL (`base < band × FTE`, no division), and shown via the domain | `_Directory.band_position` in `repositories/employees.py` |
| Read-only rows are selected as plain columns, not ORM objects | directory query |
| One FX rate set per request, not one per row | `DirectoryService` |

`EXPLAIN QUERY PLAN` on the directory query shows every join using an index or primary key. The full 10,000-row read takes about **50 ms** of SQL and fetching.

## What was changed to meet the budget

The first measurement put every insight endpoint at about **290 ms p95**, with two over the budget (300 and 314 ms). Profiling one full load:

| Cost | Before | After |
|---|---:|---:|
| SQL and fetching 10,000 rows | ~115 ms (building 19,000 ORM objects) | ~50 ms (plain columns) |
| Rows into records | ~75 ms | included above |
| A new `FxRates` table for every row | ~45 ms | 0 (one per request) |

That brought the insight endpoints to about 230–260 ms p95.

## Why the insights cost more, and what's next if they grow

Insights compute band position, USD amounts and medians **at read time** for every current employee, by design: FX rates and bands change, so stored values would go stale (ARCHITECTURE §4). SQLite also has no percentile function, so medians are computed in the domain. That gives the same answers on SQLite and Postgres. The cost is roughly linear in headcount: about 220 ms for 10,000 people, of which ~50 ms is SQL and the rest is Python working through the rows.

If headcount grows well beyond 10,000, or the budget tightens, the next steps in order would be:

1. **Load the people once per request** for screens that call several insight endpoints (Overview calls summary and exceptions), or cache the result for a given `as_of` until the next write.
2. **Push the simple aggregates into SQL** (headcount, totals, band counts with `GROUP BY`), and keep only medians in Python.
3. **On Postgres, use `percentile_cont`** for medians, if dropping SQLite parity becomes acceptable.

## Seeding

The full seed loads in about **1.5 s** on SQLite, against a 15 s target. The first version took 13.6 s, because SQLAlchemy's ORM bulk insert with `RETURNING` issued one statement per row; batched Core inserts fixed it (see the Phase 4 notes in [AI_USAGE.md](AI_USAGE.md)).
