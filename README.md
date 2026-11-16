# ACME Salary Management

Salary management for an HR Manager looking after 10,000 employees across 8 countries. It covers full salary packages (base, allowances, bonus, commission and one-time payments), effective-dated history, pay bands, and insights into how the organisation pays people.

| | |
|---|---|
| **Live app** | _Not deployed yet. The URL goes here after the first deploy ([DEPLOYMENT.md](docs/DEPLOYMENT.md))._ |
| **API health** | _Same: `https://<api>.onrender.com/api/v1/health`_ |

## What it does

- **Directory** of 10,000 employees, with server-side search, filters, sorting and CSV export. Filters are kept in the URL.
- **Profile** for each employee:
  - their full package, annualised, in local currency and in USD
  - the "how is this calculated?" breakdown
  - a band gauge with compa-ratio
  - effective-dated history
- **Hire, revise and terminate:**
  - Promotions apply the new role's default components.
  - A live preview shows the new total and band position before anything is saved.
  - Future-dated changes stay *pending* until their effective date.
- **Exceptions** to work through: people below band, above band, missing a package, or with pending changes.
- **Insights:**
  - headcount, joiners and leavers, median and total pay
  - pay by country, department or level
  - fixed vs variable pay, position against bands, and a pay histogram
  - drill-down to one country, department, level or type, in local currency

## Architecture in brief

```
Browser ──▶ Next.js 15 (Vercel) ──/api/*──▶ FastAPI (Render, Docker) ──▶ Postgres (Render)
```

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 and Alembic. It's layered api → services → domain and repositories. All salary rules live in a pure, fully tested domain layer.
- **Money:** stored as integer minor units with a currency. USD figures and band positions are computed at read time from versioned reference FX rates.
- **Frontend:** Next.js App Router, TypeScript, shadcn/ui, TanStack Query and Table, React Hook Form + Zod, and Recharts. It's light theme only.
- **One origin:** the browser only talks to Next.js, which proxies `/api/*` to FastAPI. So there's no CORS, and the session cookie (HttpOnly, signed) stays first-party.
- **Databases:** SQLite in development and tests, Postgres in production. Only portable SQL is used.

There's more in [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it locally

Pick one way.

**With Python and Node** (SQLite, hot reload): follow the **[setup guide](docs/SETUP_GUIDE.md)**. In short:

```bash
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
cp .env.example .env && python -m app.core.hash_password   # paste the printed values into .env
alembic upgrade head && python -m app.seed
uvicorn app.main:create_app --factory --reload             # API on :8000
```

```bash
cd frontend && npm install && cp .env.example .env.local && npm run dev   # app on :3000
```

**With Docker** (Postgres, as in production): create `backend/.env` with the HR login as above, then run these from the repository root:

```bash
docker compose up --build
```

```bash
docker compose run --rm api python -m app.seed
```

Then open http://localhost:3000 and sign in with `HR_ADMIN_EMAIL` and the password you hashed. The API docs are at http://localhost:8000/docs.

## Tests and checks

CI runs the same commands on every push and pull request. The git hooks run them locally (see [CONTRIBUTING.md](CONTRIBUTING.md)).

```bash
cd backend
ruff check . && ruff format --check . && mypy && pytest
```

```bash
cd frontend
npm run lint && npm run typecheck && npm test && npm run build
```

To time the endpoints against the seeded data, run `python scripts/time_endpoints.py` from `backend/`. The results are in [PERFORMANCE.md](docs/PERFORMANCE.md): every list and insight endpoint is within the 300 ms p95 budget.

## Deployment

The API (Docker) and Postgres run on Render, from [render.yaml](render.yaml). The web app runs on Vercel. Migrations run when the API starts, and the demo data is loaded once with `python -m app.seed`. [DEPLOYMENT.md](docs/DEPLOYMENT.md) lists every value to set.

## Docs

| Doc | What it covers |
|---|---|
| [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | Running it locally, step by step, with troubleshooting |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Render and Vercel setup, the values to set, seeding, Docker Compose |
| [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | The demo walkthrough, including "promote Ravi Kumar to L4" |
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | Goal, prioritised scope (MoSCoW), what's out of scope and why |
| [COMPENSATION_MODEL.md](docs/COMPENSATION_MODEL.md) | Domain model, calculation rules, edge cases E1–E25 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Stack, layering, data model, API, auth, performance, testing, trade-offs |
| [PRODUCT_DESIGN.md](docs/PRODUCT_DESIGN.md) | Persona, brand archetype, voice, colour tokens, user journey |
| [UI_DESIGN.md](docs/UI_DESIGN.md) | Screens and design decisions; sources in [docs/design/](docs/design/) |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | Endpoint timings against the 300 ms budget, and what made them fast |
| [AI_USAGE.md](docs/AI_USAGE.md) | How AI was used, and where its output was corrected |
| [Collaboration.md](Collaboration.md) | Commit message rules, branches, PRs, git hooks and CI checks |

## Known limitations

- **One login.** There's a single HR Manager account, set by environment variables. There's no user management, roles or approval workflow ([REQUIREMENTS §5](docs/REQUIREMENTS.md#5-deliberately-out-of-scope-and-why) explains why).
- **No audit trail of who changed what.** Each change records its reason and effective date, but with one user there's no "changed by".
- **Fixed reference FX rates.** USD figures use a versioned rate table, not live rates. That's deliberate, so the figures are reproducible.
- **Company-wide insights are the slowest endpoints,** at roughly 240–290 ms p95 on SQLite. They aggregate in Python for identical results on SQLite and Postgres. Filtered views are under 100 ms. On local Postgres they are within 10–30 ms of SQLite; Render itself hasn't been measured.
- **The free hosting plans sleep and expire.** The API sleeps after about 15 idle minutes (the first request then takes up to a minute), and the free Postgres database expires after 30 days.
- **Not built:** payroll, tax, equity, benefits, pay-equity analytics, bulk CSV import and merit-cycle planning ([REQUIREMENTS §3–5](docs/REQUIREMENTS.md)).
- **Synthetic data only.** The seed generates 10,000 fictional employees from a fixed random seed.
