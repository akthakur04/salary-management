# Contributing

How we work on this repository: commit messages, branches, pull requests, and the checks that enforce them. Every commit, whether written by a person or by an AI assistant, follows these rules.

## 1. Commit messages: Conventional Commits

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), the industry-standard format used by Angular, Electron, and many others. A consistent format makes the history readable as a story of how the solution evolved, and lets tools parse it.

### Format

```
<type>(<optional scope>): <description>

<optional body>

<optional footer(s)>
```

### Types

| Type | Use it for | Example |
|---|---|---|
| `feat` | A new behaviour for the user or API | `feat: add /api/v1/health` |
| `fix` | A bug fix | `fix: round compa-ratio half-to-even` |
| `test` | Adding or correcting tests only | `test: part-time employee is compared at FTE` |
| `refactor` | A code change that neither fixes a bug nor adds a feature | `refactor: extract band position calculation` |
| `perf` | A change that improves performance | `perf: index current-version lookup` |
| `docs` | Documentation only | `docs: add traceability table for E1–E25` |
| `style` | Formatting only, no behaviour change | `style: apply ruff format` |
| `build` | Build system or dependencies | `build: add PyJWT for session tokens` |
| `ci` | CI configuration | `ci: check commit messages on pull requests` |
| `chore` | Maintenance that fits none of the above | `chore: scaffold backend package` |
| `revert` | Reverts an earlier commit | `revert: feat: add CSV export` |

### Scope (optional)

A noun in parentheses naming the area changed: `backend`, `frontend`, `domain`, `api`, `seed`, `auth`, `deps`. For example `feat(domain): add Money value object`. Leave it out when the change spans several areas.

### Description (the first line)

- **Imperative mood**, as if completing "This commit will…": `add`, not `added` or `adds`.
- **Lowercase** first letter, and **no full stop** at the end.
- **At most 72 characters** for the whole first line, including the type.
- Say **what** changes, not how: `reject overlapping compensation versions`, not `update validate.py`.

### Body (optional)

- One blank line after the description.
- Explain **why** the change is needed and any trade-off. The diff already shows what changed.
- Wrap lines at 72 characters.

### Footers (optional)

- `BREAKING CHANGE: <what breaks and how to migrate>`, or a `!` after the type (`feat(api)!: rename band_position values`), for an incompatible API or schema change.
- `Refs: #12` to link an issue or pull request.
- `Co-Authored-By: Name <email>` when someone else, including an AI assistant, wrote part of the change.

### Good and bad examples

| Good | Not | Why |
|---|---|---|
| `feat(domain): reject bonus percentages outside 0–100` | `Added validation` | Missing type; past tense; vague |
| `fix: keep current package until a future raise takes effect` | `fix: Fixed bug.` | Capitalised, full stop, says nothing |
| `test: one-time payments are excluded from total pay` | `tests` | Missing type and description |
| `refactor(api): map domain errors in one handler` | `feat: refactor stuff and fix tests and add docs` | Mixes three changes; split it |

### One change per commit

Each commit is a single, self-contained step that a reviewer can understand on its own. Don't mix a refactor with a feature, or formatting with a fix.

### Test-first pairs

Domain and service logic is written test-first, and the history shows it:

1. `test: <behaviour>`: adds the failing test. This is the **only** kind of commit allowed to leave the suite red.
2. `feat: <behaviour>` or `fix: <behaviour>`: makes it pass.

Every other commit leaves lint, type checks and tests green.

## 2. Branches and pull requests

- **`dev` is the integration branch; `main` is the release branch.** Branch from an up-to-date `dev`, one branch per piece of work, named `<type>/<short-description>`: `feat/seed`, `fix/fx-rounding`, `docs/housekeeping`. Pull requests target `dev`. The reviewer merges `dev` into `main` when a milestone is complete.
- Start a new branch only after the previous pull request is merged, so every pull request targets `dev` directly. Stacked pull requests aren't retargeted automatically unless their base branch is deleted after merging, which is how Phases 2 and 3 once landed on feature branches instead of the mainline.
- **Never commit directly to `main` or `dev`.** The `no-commit-to-branch` hook blocks both.
- Open a pull request that is ready for review (not a draft), with a description of what changed, how it was verified, and anything the reviewer should know.
- **Never force-push** or rewrite history that has been pushed. Fix mistakes with a new commit.
- Only the reviewer merges into `dev` and `main`.

## 3. Checks that enforce this

The same rules are checked in three places, so problems surface as early as possible and nothing reaches `main` unchecked.

| Check | Local git hook | CI |
|---|---|---|
| Commit message follows Conventional Commits: known type, lowercase scope, description starts lowercase with no full stop, blank line before the body, first line ≤ 72 chars | `commit-msg`: commitizen | `commits` job: every commit in the pull request |
| File hygiene: trailing whitespace, final newline, valid YAML/TOML, merge-conflict markers, large files, private keys | `pre-commit` | `hooks` job |
| No commits directly on `main` | `pre-commit` | GitHub branch protection on `main`, set by the repository owner |
| Python lint and formatting (ruff) | `pre-commit`: staged files | `hooks` job and `backend` job |
| Type checks (mypy, strict) | `pre-push` | `backend` job |
| Tests (pytest) | `pre-push` | `backend` job |

**Why mypy and pytest run on push, not on commit:** the first commit of a test-first pair deliberately contains a failing test, and often imports code that doesn't exist yet. Running them on push still guarantees the branch tip is green before anyone else sees it.

The tooling checks the form of a message. Whether it uses the imperative mood and describes the change clearly is checked in review.

### Set up the hooks (once per clone)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
pre-commit install
```

`pre-commit install` adds the `pre-commit`, `commit-msg` and `pre-push` hooks.

Run every hook against the whole repository:

```bash
pre-commit run --all-files
```

Check a message before committing:

```bash
cz check -l 72 --message "feat(domain): add Money value object"
```

Don't bypass the hooks with `--no-verify`. If a hook is wrong, fix the hook in its own commit.
