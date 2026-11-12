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

### Corrections during the phase

- **Ruff import order:** the pre-commit ruff hook, run from the repo root, sorted `app` imports as third-party, the opposite of ruff run from `backend/`. The fix pins `app` and `tests` as first-party. The hook also caught two compound `assert`s and a `zip` that should be `pairwise`.
- **Traceability checker:** the AI's first script reported every test as missing. It had added `-q` on top of the configured `-q`, so pytest printed per-file counts instead of test IDs. The AI fixed the script before trusting the result.

### How the output was verified

- Domain suite: 154 tests in 0.20 s, with **100% line and branch coverage** of `app/domain`. CI now fails if domain coverage drops below 100%.
- Every edge case E1–E25 maps to at least one test. A script checked that all 44 test names in the traceability table exist.
- Ravi Kumar's numbers from the profile design reproduce exactly: fixed cash ₹27,86,400, total pay ₹30,26,400, compa-ratio 0.89, and USD 36,316.80 at 0.012.
- ruff, the format check and mypy (strict) pass.
