# Setup guide: run ACME Salary on your machine

This guide takes you from the code on GitHub to signing in to the app with 10,000 demo employees. There are two ways to run it:

| | Way | Best for | Database |
|---|---|---|---|
| **A** | [**Docker**](#part-a-run-it-with-docker) (recommended) | Trying the app, demos, first-time users | Postgres, as in production |
| **B** | [**Python and Node**](#part-b-run-it-with-python-and-node) | Working on the code, with hot reload | A SQLite file |

Either way, you only ever open **http://localhost:3000** in your browser. The web app there passes `/api/*` requests on to the API.

The commands are for macOS and Linux. On Windows, use WSL.

## Which branch to use

| Branch | What's on it |
|---|---|
| **`main`** | **The latest release.** Every finished piece of work is merged here. Use this to run the app. |
| `dev` | Active development. Work in progress is merged here first, so it can be ahead of `main` and less settled. |

This guide uses `main`. Only switch to `dev` if you're working on the code ([section B8](#b8-before-you-commit-hooks-tests-and-checks)).

---

# Part A: run it with Docker

Docker runs three containers for you: the Postgres database, the API and the web app. You don't need Python or Node installed. The first run takes about 10 minutes, most of it downloading and building.

## A1. Install the prerequisites

| Tool | Get it from | Check with |
|---|---|---|
| Git | https://git-scm.com, or `xcode-select --install` on macOS | `git --version` |
| Docker Desktop | https://www.docker.com/products/docker-desktop | `docker compose version` |

Start **Docker Desktop** and wait until it says it's running. Every `docker` command below needs it.

## A2. Get the code from GitHub

1. Open a terminal and go to the folder you want the project in, for example:

   ```bash
   cd ~/Projects
   ```

2. Copy the code from GitHub:

   ```bash
   git clone https://github.com/akthakur04/salary-management.git
   ```

3. Go into the project folder. **Run every command from here on in this folder** unless a step says otherwise:

   ```bash
   cd salary-management
   ```

4. Make sure you're on the latest release:

   ```bash
   git checkout main
   ```

   ```bash
   git pull
   ```

## A3. Create the settings file

The API reads its settings from `backend/.env`. Start from the example:

```bash
cp backend/.env.example backend/.env
```

`backend/.env` is git-ignored, so it stays on your machine. Never commit it. You'll fill in the login in step A5.

You can leave the database settings as they are: Docker replaces them with its own Postgres database.

## A4. Build the images

```bash
docker compose build
```

This downloads the base images and installs the Python and Node packages. It takes several minutes the first time. Later builds reuse what's already downloaded, so they're much quicker.

If it fails with `ReadTimeout` or `Could not find a version that satisfies the requirement`, see [Troubleshooting](#a10-docker-troubleshooting).

## A5. Create your password

The app has a single HR Manager login. You choose its password, and the app stores only a **hash** of it: a scrambled form that it can check a password against, but can't turn back into the password.

1. Generate the hash. This uses the API image you just built:

   ```bash
   docker compose run --rm --no-deps api python -m app.core.hash_password
   ```

2. Type the password you want, press Enter, then type it again. Nothing appears as you type; that's on purpose. It prints two lines:

   ```
   HR_ADMIN_PASSWORD_HASH=$2b$12$...
   SESSION_SECRET=...
   ```

3. Open `backend/.env` in any editor, for example:

   ```bash
   open -e backend/.env
   ```

4. Set these three lines, and save the file:

   | Setting | Set it to |
   |---|---|
   | `HR_ADMIN_EMAIL` | The email you'll sign in with, for example `meera.iyer@acme.example`. It doesn't have to be a real mailbox. |
   | `HR_ADMIN_PASSWORD_HASH` | The first printed line's value, copied exactly. The `$` signs are part of it. |
   | `SESSION_SECRET` | The second printed line's value. |

**Remember the password**, for example in your password manager. It can't be recovered from the hash. If you forget it, see [A9: change the password](#change-the-password).

## A6. Start the app

```bash
docker compose up -d
```

`-d` runs the containers in the background. When the API starts, it creates the database tables. Check that all three containers are running:

```bash
docker compose ps
```

You should see `db`, `api` and `web`, with `db` and `api` shown as `healthy`. The API can take about 20 seconds to get there. You can also check the API directly:

```bash
curl http://localhost:8000/api/v1/health
```

It answers `{"status":"ok","database":"ok"}`.

## A7. Load the test data

The database starts empty. Load the demo data set once:

```bash
docker compose run --rm api python -m app.seed
```

It prints `Loaded 10,000 employees and 26,776 compensation versions...`. The data is made up and the same on every run: 8 countries, 125 roles, pay bands and several years of salary history.

Running it again changes nothing, because the data is already there. To throw away your changes and start fresh, see [A9: reset the test data](#reset-the-test-data).

## A8. Sign in and look at the test data

1. Open **http://localhost:3000**. You're sent to the sign-in page.
2. Sign in with the `HR_ADMIN_EMAIL` and the password from step A5.
3. You land on the **Overview**: headcount, total pay, median pay and how many people are paid within their band.

Then look around:

| To see | Do this |
|---|---|
| Everyone | **Directory** in the sidebar. Search, filter by country or department, sort, or export to CSV. |
| One employee | Press **⌘K** (Ctrl+K on Windows or Linux), type `Ravi` and pick **Ravi Kumar**. His profile shows his package, his position in the pay band and his salary history. |
| A pay change | On Ravi's profile, choose **Revise compensation**. Promote him to L4 with **+12%** and watch the live preview: he's still below the L4 band. Nothing is saved until you confirm. |
| What needs attention | **Exceptions**: people below or above their band, missing a package, or with pay changes coming up. |
| How pay compares | **Insights**: pay by country, department or level. Filter to India to see amounts in rupees. |

[DEMO_SCRIPT.md](DEMO_SCRIPT.md) walks through all of this step by step. The API's own documentation is at http://localhost:8000/docs.

## A9. Everyday commands

| To | Run |
|---|---|
| Stop the app (your data is kept) | `docker compose down` |
| Start it again | `docker compose up -d` |
| See what the API is doing | `docker compose logs -f api` (Ctrl+C to stop watching) |
| Get the latest code and rebuild | `git pull` then `docker compose up -d --build` |

### Reset the test data

This deletes every change you've made and loads the demo data again:

```bash
docker compose run --rm api python -m app.seed --reset
```

### Change the password

Use this if you've forgotten the password or want a new one.

1. Generate a new hash, as in step A5:

   ```bash
   docker compose run --rm --no-deps api python -m app.core.hash_password
   ```

2. In `backend/.env`, replace the `HR_ADMIN_PASSWORD_HASH` line with the new value. You can keep the existing `SESSION_SECRET`.

3. Restart the API so it reads the new value:

   ```bash
   docker compose up -d --force-recreate api
   ```

### Delete everything

This removes the containers **and the database**, so you'd need to load the test data again:

```bash
docker compose down -v
```

## A10. Docker troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop isn't running. Start it and wait until it's ready. |
| `env file .../backend/.env not found` | You skipped [step A3](#a3-create-the-settings-file). Run `cp backend/.env.example backend/.env`. |
| The build fails with `ReadTimeout` or `from versions: none` while installing Python packages | Docker can't download from PyPI fast enough over your network. Builds use IPv4 only, and some networks have a slow IPv4 route to PyPI. Run `docker compose build` again on another network, such as a phone hotspot. After one successful build the packages are cached, so later builds work on your usual network. |
| `api` keeps restarting, and `docker compose logs api` says `The HR login isn't configured` | One of the three login settings in `backend/.env` is missing or wrong. Redo [step A5](#a5-create-your-password), then run `docker compose up -d --force-recreate api`. |
| "That email and password don't match" | The password doesn't match the hash in `backend/.env`. [Change the password](#change-the-password). |
| You sign in but land back on the sign-in page (often in **Safari**) | The browser dropped the session cookie on plain `http://localhost`. Use Chrome or Firefox, or set `COOKIE_SECURE=false` in `backend/.env` (local only) and run `docker compose up -d --force-recreate api`. |
| The app loads but every list is empty | The test data isn't loaded. Run [step A7](#a7-load-the-test-data). |
| `port is already allocated` for 3000, 8000 or 5432 | Another program is using that port, often a copy of the app started the Python and Node way. Stop it, then run `docker compose up -d` again. |

---

# Part B: run it with Python and Node

Use this when you're changing the code: both processes reload when you save a file. It uses a SQLite file instead of Postgres. You'll run two processes:

| Process | What it is | Address |
|---|---|---|
| **API** | FastAPI backend (Python), with a SQLite database file | http://localhost:8000 |
| **Web** | Next.js frontend, which passes `/api/*` on to the API | http://localhost:3000 |

On Windows, swap `source .venv/bin/activate` for `.venv\Scripts\activate`.

## B1. Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | **3.12** | `python3.12 --version` |
| Node.js | **22** (20 also works) | `node --version` |
| npm | comes with Node | `npm --version` |

## B2. Get the code

Clone it as in [step A2](#a2-get-the-code-from-github). To run the latest release, stay on `main`. To work on the code, switch to the development branch:

```bash
git checkout dev
```

## B3. Backend: install

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

From now on, run backend commands from `backend/` with the virtual environment active. Your prompt shows `(.venv)` when it is.

## B4. Backend: configure the login

The API refuses to start until all three login settings are in place.

1. Copy the example settings:

   ```bash
   cp .env.example .env
   ```

2. Generate a password hash and a session secret. It asks for the password twice, without showing it:

   ```bash
   python -m app.core.hash_password
   ```

3. Open `backend/.env` and set `HR_ADMIN_EMAIL`, `HR_ADMIN_PASSWORD_HASH` and `SESSION_SECRET`, as in the table in [step A5](#a5-create-your-password).

The other settings already have sensible local defaults:

| Setting | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./salary.db` | The database file, created in `backend/` |
| `COOKIE_SECURE` | `true` | The session cookie is marked Secure. Chrome and Firefox accept that on `http://localhost`; see [Troubleshooting](#b7-troubleshooting) for Safari. |
| `SESSION_HOURS` | `8` | How long a sign-in lasts |
| `PENDING_WINDOW_DAYS` | `60` | How far ahead a scheduled pay change counts as "due soon" in Exceptions |

## B5. Backend: create the database, load the test data and start

1. Create the tables. Run this again whenever you pull new migrations:

   ```bash
   alembic upgrade head
   ```

2. Load the test data, as in [step A7](#a7-load-the-test-data). Add `--reset` to throw away your changes and load it fresh:

   ```bash
   python -m app.seed
   ```

3. Start the API, and leave this terminal running:

   ```bash
   uvicorn app.main:create_app --factory --reload
   ```

4. In another terminal, check it's up:

   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## B6. Frontend: install and start

In a **new terminal**, from the project folder:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

`.env.local` sets `API_ORIGIN=http://localhost:8000`, which is where the frontend sends `/api/*`. If your API runs elsewhere, change it there.

Then open http://localhost:3000 and sign in, as in [step A8](#a8-sign-in-and-look-at-the-test-data).

## B7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `RuntimeError: The HR login isn't configured: ...` when starting the API | One of the three login settings is missing or wrong, and the error says which. Redo [step B4](#b4-backend-configure-the-login). The hash must start with `$2`, and the secret must be at least 32 characters. |
| "That email and password don't match" with the right password | The hash in `.env` doesn't match the password. Run `python -m app.core.hash_password` again, paste the new hash, and restart the API. |
| Sign-in succeeds but you land back on the sign-in page (often in **Safari**) | The browser dropped the Secure session cookie on plain `http://localhost`. Set `COOKIE_SECURE=false` in `backend/.env` for local development only, and restart the API. |
| `no such table: employee` or similar | Migrations haven't run against this database. Run `alembic upgrade head` from `backend/`. |
| Pages show "We couldn't load this" | The API isn't running, or isn't at `API_ORIGIN`. Check `curl http://localhost:8000/api/v1/health`. |
| `Port 3000 is in use` | Something else is using port 3000, perhaps the Docker version. Run `npm run dev -- --port 3100` and open http://localhost:3100. |
| `Address already in use` for the API | Start it on another port with `uvicorn app.main:create_app --factory --reload --port 8001`, and set `API_ORIGIN=http://localhost:8001` in `frontend/.env.local`. |
| `Cannot find module './NNN.js'` in the browser | You ran `npm run build` while `npm run dev` was running, and they share the `.next` folder. Stop the dev server, delete `frontend/.next`, and start it again. |
| `python3.12: command not found` | Install Python 3.12 (python.org, Homebrew `brew install python@3.12`, or pyenv) and repeat [step B3](#b3-backend-install). |

## B8. Before you commit: hooks, tests and checks

Work happens on `dev`: branch from it and open pull requests into it. `main` only receives releases, merged from `dev`. The full rules are in [CONTRIBUTING.md](../CONTRIBUTING.md).

Install the git hooks once per clone, from the project folder, with the backend virtual environment active:

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

To time the list and insight endpoints against the seeded data, run this from `backend/` with the virtual environment active. The results are recorded in [PERFORMANCE.md](PERFORMANCE.md).

```bash
python scripts/time_endpoints.py
```

## B9. Daily workflow, once set up

```bash
# Terminal 1
cd backend && source .venv/bin/activate
alembic upgrade head          # only if new migrations were pulled
uvicorn app.main:create_app --factory --reload

# Terminal 2
cd frontend && npm run dev
```
