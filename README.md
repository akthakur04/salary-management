# ACME Salary Management

Salary management for an HR Manager looking after 10,000 employees across 8 countries: full salary packages (base, allowances, bonus, commission, one-time payments), effective-dated history, pay bands, and insights into how the organisation pays people.

> **Status:** in progress. The backend foundation and the domain layer (all salary rules, edge cases E1–E25) are in place; persistence, seed, API and frontend follow phase by phase.

## Docs

| Doc | What it covers |
|---|---|
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | Goal, prioritised scope (MoSCoW), what's out of scope and why |
| [COMPENSATION_MODEL.md](docs/COMPENSATION_MODEL.md) | Domain model, calculation rules, edge cases E1–E25 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Stack, layering, data model, API, auth, performance, testing, trade-offs |
| [PRODUCT_DESIGN.md](docs/PRODUCT_DESIGN.md) | Persona, brand archetype, voice, colour tokens, user journey |
| [UI_DESIGN.md](docs/UI_DESIGN.md) | Screens and design decisions; sources in [docs/design/](docs/design/) |
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
(cd .. && pre-commit install)   # git hooks, see CONTRIBUTING.md
uvicorn app.main:create_app --factory --reload
```

The API is at http://localhost:8000/api/v1 (health check: `/api/v1/health`), with interactive docs at http://localhost:8000/docs.

### Checks

Run from `backend/`; CI runs the same commands on every push and pull request.

```bash
ruff check .
ruff format --check .
mypy
pytest
```
