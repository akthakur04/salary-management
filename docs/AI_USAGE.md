# AI Usage Log

This project was built with an AI coding assistant (Claude Code) working as a pair: the candidate reviews and steers, and the AI implements. This log records the key prompts, what the AI generated, **where the candidate overrode or corrected it**, and how each output was verified. It is updated in every PR.

- **Master prompt for the build phases:** [prompts/MASTER_PROMPT.md](prompts/MASTER_PROMPT.md), saved verbatim.

## Design phase (before any code)

The AI drafted the requirements, compensation model, architecture, product design and UI screens from the brief. The candidate reviewed each draft and corrected it in these places:

| # | What the AI proposed | What the candidate decided | Why |
|---|---|---|---|
| D1 | A "compensation management" product | Reframed as **salary management** with full packages (base, allowances, bonus, commission, one-time); payroll explicitly excluded | The candidate checked the brief's exact wording. It asks for salary data management and pay insights, not payroll. |
| D2 | MUI on a Vite single-page app | **Next.js (App Router) + shadcn/ui** | Owned, Tailwind-styled components for a modern look; Next.js gives routing, middleware and same-origin `/api` proxying. |
| D3 | No authentication | **Env-based single HR login** (M9) | Salary data shouldn't be public, even in a demo deployment. |
| D4 | Store USD amounts and compa-ratio on each compensation version | Store only local-currency totals; **compute USD and compa-ratio at read time** | Caught in design review as a stale-data risk: FX rates and pay bands change, so stored values would silently go out of date. |
| D5 | Light and dark themes | **Light theme only** | Cuts scope; dark mode doubles the colour and contrast work for every status state. |
| D6 | Trim the requirements doc to one page | **Keep it detailed** | The candidate preferred a complete record of scope, decisions and exclusions. |

## Phase 1: Backend foundation

### Kick-off review

Before writing code, the AI read all the docs and screen sources and raised nine questions where the docs were silent, inconsistent, or would need a model or API change. The candidate decided each one. They are implemented in the phase noted, and the affected docs are updated in that phase's PR.

| # | Question the AI raised | Candidate's decision | Phase |
|---|---|---|---|
| Q1 | `compensation_version` has no role or country, so a future-dated promotion would switch the employee's band immediately, and history couldn't show "L2 → L3" (E14, E17, E18) | **Store `role_id` and `country_code` on each version.** Band comparison uses the version in force at `as_of`. | 3 |
| Q2 | The revise page's live preview has no endpoint, and the UI shouldn't duplicate domain logic | **Add a dry-run endpoint**, `POST /employees/{id}/compensation/preview`, using the same validation and calculation as the save | 5 |
| Q3 | Overview needs joiners/leavers and recent pay changes, which the API doesn't cover; the fourth KPI differs between PRODUCT_DESIGN (% bonus-eligible) and the design (% in band) | **Extend the API** (joiners/leavers in `/insights/summary`, add `GET /insights/recent-changes`); **follow the design** for the KPI | 5 |
| Q4 | "Pending changes" is "next 60 days" in the design but "any future date" in E14 | **Next 60 days** for Exceptions and the sidebar badge (configurable); profiles show every future version | 3/5 |
| Q5 | E15: a backdated correction dated between two existing versions | **Reject with `409 OVERLAPPING_VERSION`** unless it falls on or after the start of the latest in-force version | 2/3 |
| Q6 | A hire page is in ARCHITECTURE but not in the route list or the designs | **Build a simple form** at `/employees/new` | 6 |
| Q7 | Profile peer stats ("peers in role & country", peer median) | Part of `GET /employees/{id}` | 5 |
| Q8 | Dependencies not named in the prompt: `pydantic-settings`, `uvicorn`, `PyJWT`, `psycopg[binary]`, `httpx`, `pytest-cov` | **Approved** | 1–7 |
| Q9 | mypy strict only on `domain/`, or on all of `app/` | **Strict on all of `app/`** (and tests) | 1 |

### What the AI generated

- **Prompt:** the master prompt, Phase 1 section.
- **Output:** the layered `backend/` package, `pyproject.toml` (ruff, strict mypy, pytest), settings from env, the database engine and session factory, an injectable `Clock`, an app factory with `GET /api/v1/health`, the single error handler, the GitHub Actions CI workflow, `.env.example` and a README stub.
- **Test-first:** the clock, health check and error shape were each committed as a failing test (`test:`) before the implementation (`feat:`).

### Corrections during the phase

- The AI's first clock test passed in a time that was already converted to UTC, so it couldn't fail if the clock skipped the conversion. The AI caught this during its own review and fixed the test, before pushing, so it now uses a New York evening that is already the next day in UTC.
- The first scaffold commit included the generated `*.egg-info` build folder. It was removed and added to `.gitignore` before pushing.

### Candidate's addition: commit rules and git hooks

- **Prompt:** the candidate asked whether pre-commit checks existed (they didn't) and asked for a contribution guide defining industry-standard commit guidelines, enforced by pre-commit, ruff and CI.
- **Output:** `CONTRIBUTING.md` (Conventional Commits 1.0.0, branches, PRs); `.pre-commit-config.yaml` (hygiene hooks and ruff on commit, a commit-message check, mypy and pytest on push); `.cz.toml` (commitizen rules); and two new CI jobs that check every commit message in a PR and run the hooks.
- **Design choice:** mypy and pytest run on push, not on commit, so the deliberately failing first commit of a TDD pair can still be recorded.
- **Found while verifying:** commitizen's built-in preset accepted `fix: Fixed bug.` and ignored the 72-character limit set in its config file. The AI replaced the preset with a stricter pattern (lowercase description, no full stop, blank line before the body). It now passes the limit on the command line in the hook and in CI.

### How the output was verified

- `ruff check .`, `ruff format --check .` and `mypy` (strict) all pass.
- `pytest`: 13 tests pass in under 0.1 s.
- The real server was started with `uvicorn app.main:create_app --factory`. `/api/v1/health` returned `{"status":"ok","database":"ok"}`, an unknown route returned the standard error shape, and `/docs` loaded.

## Phase 2: Domain, test-first

- **Prompt:** "go, do and raise a separate PR for it", for Phase 2 of the master prompt.
- **Output:** the pure-Python domain in `backend/app/domain/`:
  - `Money` and the domain errors
  - pay components
  - package totals
  - role defaults
  - employment rules and pay-band comparison
  - FX conversion
  - effective-dated version rules
  - pay summaries and band distribution
  - employee identity
  - a test that keeps the domain free of framework imports
  - a traceability table in `COMPENSATION_MODEL.md` §5
- **Test-first:** each module was committed as a failing `test:` commit, then a `feat:` commit that makes it pass.

### Decisions the AI made, for review

These follow from the docs or from the kick-off answers, but the docs didn't spell them out:

| Decision | Reasoning |
|---|---|
| Role defaults are bonus or commission **percentages** only | A role spans every country and currency, so a fixed default amount (₹ vs $) would be meaningless. Allowances are set per employee. |
| A 0% bonus or commission is rejected | E20 rejects zero components. HR removes the component instead. |
| The first version must be a `hire`, and `hire` is only allowed first | Keeps history meaningful, and matches the seed and the hire service. |
| A new change must start after the latest version, even when that version is future-dated | This follows from Q5 and E16. Allowing it would create an overlap with the pending change. |
| A same-date correction supersedes the latest version, which stays in history with a zero-length period | Q5 allowed a correction "on" the latest start date. The zero-length period keeps the record while it never counts as in force. |
| Compa-ratio is rounded to two decimals; raise % and variable share to one | Matches the design (0.89, +9.1%). |
| USD always has rate 1 | USD per USD is 1 by definition, so the rate set doesn't need it. |

**Candidate's decision on review:** the AI asked whether moves to another country (E18) should get their own reason, rather than borrowing `market_adjustment`. The candidate chose to **add `transfer`**, so the reasons are hire, promotion, merit, market adjustment, transfer and correction.

### Corrections during the phase

- **Ruff import order:** the pre-commit ruff hook, run from the repo root, sorted `app` imports as third-party, the opposite of ruff run from `backend/`. The fix pins `app` and `tests` as first-party. The hook also caught two compound `assert`s and a `zip` that should be `pairwise`.
- **Traceability checker:** the AI's first script reported every test as missing. It had added `-q` on top of the configured `-q`, so pytest printed per-file counts instead of test IDs. The AI fixed the script before trusting the result.

### How the output was verified

- Domain suite: 154 tests in 0.20 s, with **100% line and branch coverage** of `app/domain`. CI now fails if domain coverage drops below 100%.
- Every edge case E1–E25 maps to at least one test. A script checked that all 44 test names in the traceability table exist.
- Ravi Kumar's numbers from the profile design reproduce exactly: fixed cash ₹27,86,400, total pay ₹30,26,400, compa-ratio 0.89, and USD 36,316.80 at 0.012.
- ruff, the format check and mypy (strict) pass.

## Phase 3: Persistence

- **Prompt:** "start phase 3 and raise a separate PR".
- **Output:**
  - ORM models and constraints
  - an exact-decimal column type
  - the first Alembic migration, with a test that the migrated schema matches the models
  - repositories for reference data, compensation history and the employee directory
  - hire, revise and terminate services, each in one transaction
  - a directory service that adds the domain's band comparison and USD figures
- **Test-first:** repositories, services and the directory were each committed as failing `test:` commits before the `feat:` commits.

### Decisions the candidate made at the start of the phase

The AI raised two questions before writing any code:

| Question | Candidate's decision |
|---|---|
| Should the employee row keep its own role and country, now that each version stores them? Keeping them would leave a future-dated promotion stale until something updated them. | **Read them from the version in force.** The columns were dropped from `employee`, and the directory joins the version in force on `as_of`. |
| What should happen when an employee with a saved future change is terminated before that change takes effect? | **Reject with `409 PENDING_CHANGE_AFTER_TERMINATION`.** Revising a terminated employee is rejected too. |

### Decisions the AI made, for review

| Decision | Reasoning |
|---|---|
| FX rates, FTE and percentages use an `ExactDecimal` type: NUMERIC on Postgres, text on SQLite | SQLite would round them through floating point. The migration test confirms the schema still matches the models. |
| A revision without components carries over the recurring components only | A one-time payment belongs to the version it was recorded in; copying it forward would count it twice in its payout year. |
| Carried-over fixed amounts keep their original currency | A transfer must restate allowances in the new currency. Otherwise ₹30,000 would silently become €30,000. |
| Before their start date, a future hire shows the role and country of their first version, with no current package | They still appear in the directory with the right role and country. |
| ~~Termination dates must fall between the hire date and today~~ | Replaced on review (see below). |
| Directory band filter in SQL, display values from the domain | SQL is needed to filter and count. A parametrised test checks the SQL position matches the domain comparison for every position. |

### Candidate's decision on review: future termination dates

The AI pointed out that three rules together made some employees impossible to terminate: "reject a termination with a pending change after it", "no future termination dates" and "versions can't be withdrawn". Anyone with a pending raise could only be terminated after the raise took effect. The candidate chose to **allow future termination dates**:

- Terminating records the last day worked and nothing else.
- Status is worked out from that date at read time (`status_on` in the domain, and the same rule in the directory query). The employee counts as terminated from the day after, with no job needed to flip the status.
- HR can date a termination on or after a pending change.
- A pay change dated after the last day is rejected with `CHANGE_AFTER_TERMINATION`.
- `EmployeeService` no longer needed its clock, so the AI removed that dependency.

### Corrections during the phase

- **Migration types:** Alembic rendered the custom decimal type as `app.models.types.ExactDecimal()`, with no import and no precision. The AI fixed it by hand and confirmed the schema comparison can detect drift by adding a column in memory.
- **Wrong test expectations:** the AI's first directory test had two wrong expected values. Every employee code started with `EMP-0`, so that filter matched everyone, and Ravi has no bonus at that point. Both were caught by checking the expected numbers by hand before implementing.
- **A test-only method:** the AI first planned a repository method used only by a test, then dropped it and had the test read the stored columns directly.
- **A misleading message:** the first termination error suggested "contact support to withdraw the change", which isn't a feature. The message was rewritten.

### How the output was verified

- 244 backend tests pass in about 2 s.
- Coverage is 99% overall, with the revise service and the directory at 100%. The one uncovered line is the Postgres branch of the decimal type, which can't run on SQLite.
- Migrations upgrade to a schema identical to the models and downgrade to an empty database.
- ruff, the format check, mypy (strict, now including the migrations) and all pre-commit hooks pass.

## Phase 4: Seed

- **Prompt:** "Start Phase 4". It was the first phase branched from `dev` after PR #5 merged, so its PR targets `dev`.
- **Output:**
  - reference data: 8 countries, 8 departments, 25 families × 5 levels, a band for every role in every country, and role defaults
  - a deterministic generator for 10,000 employees with salary histories
  - regional synthetic names
  - an idempotent bulk loader
  - the `python -m app.seed` command
- **Test-first:** the generator's invariants (on a 2,000-person sample) and the loader's behaviour were each committed as failing tests before the implementation.

### Decisions the AI made, for review

| Decision | Reasoning |
|---|---|
| Place current pay against the band first, then build history backwards | It's the only way to control the "~85% in band" mix while keeping realistic merits and promotions. Every version still goes through `plan_revision`, so the seed can't create data the app would reject. |
| Pin the SE L3 and SE L4 India bands, and seed Ravi Kumar exactly as designed | The demo scenario (a 12% promotion raise that still lands below the L4 minimum) depends on those exact figures. |
| The United Kingdom uses ISO code `GB` | It's the ISO 3166 code. The brief and master prompt say "UK", and it displays as "United Kingdom". |
| Missing packages (12) and future hires (20) at fixed positions, not random draws | Every sample size then gets a predictable number, so tests don't depend on luck. |
| Loader ids come back via `RETURNING`, never written explicitly | Explicit ids would leave Postgres sequences behind, and the app's next insert would collide with seeded rows. |
| A database that already has data is left alone unless `--reset` is given | Re-running the seed against the deployed demo shouldn't wipe changes made during the demo. |

### Corrections during the phase

- **A zero sign-on bonus at full scale:** the full 10,000-person run failed, though the 2,000-person sample passed. A 5% sign-on rounded to the nearest thousand came to 0 for small part-time bases in GBP or SGD, and the domain correctly rejected it. The fix rounds to the nearest hundred, and a test now generates the full set.
- **Too few versions:** the first full run produced 21,486 versions against the ~30k the requirements plan for. The AI weighted histories towards three or four versions; recent hires cap it at ~26,800.
- **Slow loading (13.6 s):** the load fit the 15 s budget, but only just. Profiling showed SQLAlchemy's ORM bulk insert with `RETURNING` issuing one statement per row (32k statements), while SQLite itself took 0.75 s. Batched Core inserts brought it to 1.5 s.
- **Name lists:** reformatting them into comma-separated strings first split two-word names ("Wei Ling") and left empty entries. A check on the list lengths caught it before commit.

### How the output was verified

- 271 backend tests pass in about 4 s. Coverage is 99% overall; the generator, names and reference data are at 100%.
- The generator tests check, on a 2,000-person sample:
  - the same seed gives the same output
  - unique codes and emails
  - 8 departments, 125 roles and 1,000 bands
  - a valid history of 1–4 versions for each person, in the right currency
  - the employment mix, about 5% terminated with nothing due after the last day, and about 85% in band
  - about 20% overrides, plus pending changes and missing packages
  - Ravi's exact figures

  A separate test generates the full 10,000.
- The loader tests check that the data loads completely, that a second run changes nothing, that `--reset` reloads identical data, that the first 50 histories read back exactly as generated, and that the directory shows Ravi at compa-ratio 0.89 and $36,316.80.
- The real command was run against a migrated SQLite file several times: 10,000 employees, 26,776 versions and 32,249 components in about 1.5 s per load.

## Phase 5: API and authentication

- **Prompt:** "Merged, start Phase 5". The work branched from `dev`, and its PR targets `dev`.
- **Output:**
  - **Auth:** bcrypt check, HS256 JWT in an HttpOnly / Secure / SameSite=Lax cookie, one `require_session` dependency, a start-up check of the login settings, and `python -m app.core.hash_password`.
  - **Errors:** domain errors mapped to 409 or 422.
  - **Endpoints:** reference data; employees (list, CSV export, profile, history, hire, edit, terminate, revise, preview); insights (summary, breakdown, band distribution, exceptions, recent changes).
  - **Performance:** a timing script and `PERFORMANCE.md`.
- **Test-first:** auth, error mapping, reference, employee and insight endpoints were each committed as failing tests before the implementation.

### Decisions the AI made, for review

| Decision | Reasoning |
|---|---|
| Login failures return `INVALID_CREDENTIALS` (401) with the design's copy; a missing, expired or tampered session returns `UNAUTHENTICATED` | Both are 401. The distinct code lets the UI show the login error in place, instead of redirecting to the login page it's already on. A wrong email and a wrong password get identical responses, and bcrypt always runs. |
| `GET /health` is public | The hosting platform's health check can't send a cookie, and health exposes no salary data. This was noted in Phase 1 and is now in ARCHITECTURE §5a. |
| The app refuses to start without a complete login configuration | A misconfigured deploy fails at start-up instead of at the first login attempt. |
| Decimals are fixed-precision strings (`"0.89"`, `"15.00"`) | SQLite read back `15` and Postgres `15.00`. Fixed formatting makes the API identical on both, and clients never parse floats. |
| `recent-changes` takes `limit`, not `days` | Seeded versions all share one `created_at`, so a "last 7 days" window would return either nothing or everything. The endpoint lists the latest recorded changes (newest first), which is what the Overview panel shows. |
| Peers are current full- and part-time employees in the same role and country, compared on FTE-equivalent base; contractors are left out | It matches how bands are compared. |
| CSV text starting with `=`, `+`, `-` or `@` is prefixed with `'` | HR opens the export in Excel, and a crafted name shouldn't run as a formula. |
| Insights compute from all current employees in Python, reusing the tested directory query | It's one source of truth for band position and USD, and fast enough at 10k (see below). Pushing aggregates into SQL is documented as the next step. |

### Corrections during the phase

- **The route-table walk found nothing:** the first route-table test listed zero routes. FastAPI 0.162 mounts included routers lazily, so `app.routes` no longer lists endpoints. Rather than depend on private internals, the test walks the OpenAPI schema (a public, complete list of paths and methods) and sends every protected route a cookie-less request. The AI checked that the test fails by adding an unprotected route in memory.
- **Over budget:** the first timing put the insight endpoints at about 290 ms p95, two over the 300 ms budget. Profiling found ORM objects built for 10,000 read-only rows (~65 ms extra) and an FX table per row (~45 ms). Plain columns and one rate set per request brought them to about 240 ms. The SQL itself was already fully indexed (`EXPLAIN QUERY PLAN`).
- **Code left unfinished:** the AI's first insights service had a placeholder method that raised `NotImplementedError`, plus an unused parameter. The router used an `__import__` hack, and two percentages used float `round()`. All four were fixed before commit, and a shared `share_percent` was added to the domain, with tests, so every percentage rounds half-to-even.
- **Methods named `list`:** they hid Python's built-in `list` in later type annotations. They were renamed to `search`.
- **A real bug found by chasing coverage:** `update_details` set the new email on the session object before validating the FTE. A rejected edit left the change pending, and the next commit on that session saved it. A failing test showed it, and the fix validates everything before changing the row. The other write paths were checked, and they change rows only inside their transaction.

### How the output was verified

- 361 backend tests pass. Coverage is 99% overall. The domain stays at 100% coverage. ruff, the format check, mypy (strict, now also on `scripts/`) and all hooks pass.
- Auth tests cover the cookie attributes, case-insensitive email, a wrong password matching an unknown email, missing / expired / tampered / wrongly-signed sessions, logout, and refusing to start without settings. The route-table test covers all 20 protected routes.
- The preview test reproduces the demo scenario: promoting Ravi to L4 at ₹26,88,000 shows total pay ₹34,77,600, +12.0%, **below band by ₹1,12,000**, and saves nothing.
- Timings against the full seed are in `docs/PERFORMANCE.md`. Every budgeted endpoint is within 300 ms p95: directory and profile at 2–22 ms, insights at about 230–260 ms.
- **Smoke test:** a real `uvicorn` server with a `.env` holding a freshly generated hash. A request without a cookie and a wrong password each got 401, login set the expected cookie, and the summary and directory returned the seeded figures (Ravi at compa-ratio 0.89).
