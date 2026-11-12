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
