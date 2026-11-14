# ACME Salary Management

Salary management for an HR Manager looking after 10,000 employees across 8 countries: full salary packages (base, allowances, bonus, commission, one-time payments), effective-dated history, pay bands, and insights into how the organisation pays people.

> **Status:** in progress. The backend foundation, the domain layer (all salary rules, edge cases E1–E25), persistence (schema, migrations, hire / revise / terminate, the employee directory query) the 10,000-employee demo seed and the REST API with the HR login are in place; the frontend and deployment follow.

## Docs

| Doc | What it covers |
|---|---|
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | Goal, prioritised scope (MoSCoW), what's out of scope and why |
| [COMPENSATION_MODEL.md](docs/COMPENSATION_MODEL.md) | Domain model, calculation rules, edge cases E1–E25 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Stack, layering, data model, API, auth, performance, testing, trade-offs |
| [PRODUCT_DESIGN.md](docs/PRODUCT_DESIGN.md) | Persona, brand archetype, voice, colour tokens, user journey |
| [UI_DESIGN.md](docs/UI_DESIGN.md) | Screens and design decisions; sources in [docs/design/](docs/design/) |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | Endpoint timings against the 300 ms budget, and what made them fast |
| [AI_USAGE.md](docs/AI_USAGE.md) | How AI was used, and where its output was corrected |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Commit message rules (Conventional Commits), branches, PRs, git hooks and CI checks |

## Backend

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0. SQLite locally, Postgres in production.

### Run locally

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m app.core.hash_password  # paste the printed values into .env
(cd .. && pre-commit install)   # git hooks, see CONTRIBUTING.md
alembic upgrade head            # create or update the database schema
python -m app.seed               # load 10,000 demo employees (once; --reset reloads)
uvicorn app.main:create_app --factory --reload
```

The API is at http://localhost:8000/api/v1 (health check: `/api/v1/health`), with interactive docs at http://localhost:8000/docs.

Every endpoint except login and health needs the session cookie that `POST /api/v1/auth/login` sets, with the email in `HR_ADMIN_EMAIL` and the password you hashed. The endpoints are listed in [ARCHITECTURE.md §5](docs/ARCHITECTURE.md#5-api-design).

To time the list and insight endpoints against the seeded data, run `python scripts/time_endpoints.py`. The results are in [PERFORMANCE.md](docs/PERFORMANCE.md).

### Checks

Run from `backend/`; CI runs the same commands on every push and pull request.

```bash
ruff check .
ruff format --check .
mypy
pytest
```
