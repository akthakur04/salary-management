# Setup guide: run ACME Salary locally

This guide takes you from a fresh clone to signing in to the app with 10,000 demo employees. It takes about 10 minutes, most of it installing packages.

You'll run two processes:

| Process | What it is | Address |
|---|---|---|
| **API** | FastAPI backend (Python), with a SQLite database file | http://localhost:8000 |
| **Web** | Next.js frontend, which proxies `/api/*` to the API | http://localhost:3000 |

You only ever open the **web** address in your browser.

The commands below are for macOS and Linux. On Windows, use WSL, or swap `source .venv/bin/activate` for `.venv\Scripts\activate`.

---

## 1. Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | **3.12** | `python3.12 --version` |
| Node.js | **22** (20 also works) | `node --version` |
| npm | comes with Node | `npm --version` |

You don't need Docker or a database server: local development uses a SQLite file, which Python ships with. Production uses Postgres (see [ARCHITECTURE.md §9](ARCHITECTURE.md#9-deployment)).

## 2. Clone the repository

```bash
git clone https://github.com/akthakur04/salary-management.git
cd salary-management
```

Active development happens on the `dev` branch, and `main` holds released milestones. To run the latest work:

```bash
git checkout dev
```

## 3. Backend: install

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

From now on, run backend commands from `backend/` with the virtual environment active. Your prompt shows `(.venv)` when it is.

## 4. Backend: configure the login

The app has a single HR Manager login, set through environment variables. The API refuses to start until all three login settings are in place.

1. Copy the example settings:

   ```bash
   cp .env.example .env
   ```

2. Generate a password hash and a session secret:

   ```bash
   python -m app.core.hash_password
   ```

   It asks for a password twice, without echoing it, and prints two lines:

   ```
   HR_ADMIN_PASSWORD_HASH=$2b$12$...
   SESSION_SECRET=...
   ```

3. Open `backend/.env` and set:
   - `HR_ADMIN_EMAIL` to the email you'll sign in with, for example `meera.iyer@acme.example`
   - `HR_ADMIN_PASSWORD_HASH` and `SESSION_SECRET` to the two printed values

   Paste the hash exactly as printed. The `$` signs are part of it.

`backend/.env` is git-ignored. Never commit it. The plain password isn't stored anywhere; only its hash is.

The other settings in `.env` already have sensible local defaults:

| Setting | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./salary.db` | The database file, created in `backend/` |
| `COOKIE_SECURE` | `true` | The session cookie is marked Secure. Chrome and Firefox accept that on `http://localhost`; see [Troubleshooting](#9-troubleshooting) for Safari. |
| `SESSION_HOURS` | `8` | How long a sign-in lasts |
| `PENDING_WINDOW_DAYS` | `60` | How far ahead a scheduled pay change counts as "due soon" in Exceptions |

## 5. Backend: create the database and load the demo data

1. Create the tables by running the migrations:

   ```bash
   alembic upgrade head
   ```

   You should see `Running upgrade  -> 0001, Initial schema...`. Run this command again whenever you pull new migrations.

2. Load the demo data set:

   ```bash
   python -m app.seed
   ```

   It prints `Loaded 10,000 employees and 26,776 compensation versions in ~1.5 s.` The data is the same on every run: 8 countries, 125 roles, pay bands and salary histories. It includes **Ravi Kumar** (`EMP-04821`), the employee in the demo scenario.

The seed is safe to run again. If the database already has data it changes nothing, and `--reset` wipes it and loads it fresh:

```bash
python -m app.seed --reset
```

## 6. Backend: start the API

```bash
uvicorn app.main:create_app --factory --reload
```

Check that it's up. In another terminal:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","database":"ok"}
```

Interactive API docs are at http://localhost:8000/docs. Every endpoint except health and login needs a session, so try them from the app, or sign in through `POST /api/v1/auth/login` in the docs page first.

Leave this terminal running.

## 7. Frontend: install and start

In a **new terminal**, from the repository root:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

`.env.local` sets `API_ORIGIN=http://localhost:8000`, which is where the frontend proxies `/api/*`. If your API runs elsewhere, change it there.

## 8. Sign in

1. Open **http://localhost:3000**. You'll be sent to the sign-in page.
2. Sign in with the `HR_ADMIN_EMAIL` and the password you hashed in step 4.
3. You land on the **Overview**.

Try the demo journey:

1. Press **⌘K** (Ctrl+K on Windows or Linux), type `Ravi` and press Enter.
2. Open **Revise compensation**. The live preview shows the promotion to L4 with +12% still landing below the L4 band.
3. Set **Effective from** to 1 Jan 2027, then choose **Review change** and **Confirm & save**.
4. Back on the profile, the change shows as pending until that date.

To undo your changes, run `python -m app.seed --reset` in `backend/`.

---

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `RuntimeError: The HR login isn't configured: ...` when starting the API | One of `HR_ADMIN_EMAIL`, `HR_ADMIN_PASSWORD_HASH` or `SESSION_SECRET` is missing or wrong. The error says which. Redo [step 4](#4-backend-configure-the-login). The hash must start with `$2`, and the secret must be at least 32 characters. |
| "That email and password don't match" with the right password | The hash in `.env` doesn't match the password. Run `python -m app.core.hash_password` again, paste the new hash, and restart the API. |
| Sign-in succeeds but you land back on the sign-in page (often in **Safari**) | The browser dropped the Secure session cookie on plain `http://localhost`. Set `COOKIE_SECURE=false` in `backend/.env` for local development only, and restart the API. |
| `no such table: employee` or similar | Migrations haven't run against this database. Run `alembic upgrade head` from `backend/`. |
| Pages show "We couldn't load this" | The API isn't running, or isn't at `API_ORIGIN`. Check `curl http://localhost:8000/api/v1/health`. |
| `Port 3000 is in use` | Something else is using port 3000. Run `npm run dev -- --port 3100` and open http://localhost:3100. |
| `Address already in use` for the API | Start it on another port with `uvicorn app.main:create_app --factory --reload --port 8001`, and set `API_ORIGIN=http://localhost:8001` in `frontend/.env.local`. |
| `Cannot find module './NNN.js'` in the browser | You ran `npm run build` while `npm run dev` was running, and they share the `.next` folder. Stop the dev server, delete `frontend/.next`, and start it again. |
| `python3.12: command not found` | Install Python 3.12 (python.org, Homebrew `brew install python@3.12`, or pyenv) and repeat [step 3](#3-backend-install). |

## 10. Before you commit: hooks, tests and checks

Install the git hooks once per clone, from the repository root, with the backend virtual environment active:

```bash
pre-commit install
```

They check commit messages ([Conventional Commits](../CONTRIBUTING.md)), formatting and lint on commit, and run mypy and pytest on push. CI runs the same checks on every pull request.

Run the checks yourself:

```bash
# backend/
ruff check .
ruff format --check .
mypy
pytest

# frontend/
npm run lint
npm run typecheck
npm test
npm run build      # stop `npm run dev` first; they share .next
```

To time the list and insight endpoints against the seeded data (with the backend virtual environment active, from `backend/`):

```bash
python scripts/time_endpoints.py
```

The results are recorded in [PERFORMANCE.md](PERFORMANCE.md).

## 11. Daily workflow, once set up

```bash
# Terminal 1
cd backend && source .venv/bin/activate
alembic upgrade head          # only if new migrations were pulled
uvicorn app.main:create_app --factory --reload

# Terminal 2
cd frontend && npm run dev
```

Branching and pull-request rules are in [CONTRIBUTING.md](../CONTRIBUTING.md): branch from `dev`, and open pull requests into `dev`.
