# UI Design

Built in Claude Design from [PRODUCT_DESIGN.md](PRODUCT_DESIGN.md) (persona, Sage + Caregiver archetype, tokens, journey).

- **Live canvas (clickable prototype):** https://claude.ai/artifact/PyubYumTR2teGmLvix1DD9 (private until shared from the canvas's Share menu)
- **Source of each screen:** [`docs/design/`](design/), committed so the design is reviewable without access to the canvas.

## Screens (in journey order)

| # | Screen | Journey stage | What it demonstrates |
|---|---|---|---|
| 1 | **Sign in** (`Main.dc.html`) | Sign in | Single env-configured HR login (M9); generic error copy; confidentiality note. |
| 2 | **Overview** | Orient | KPI cards (headcount, total target pay, median, % in band); "Needs your attention" list deep-linking to Exceptions; median pay by country; recent changes with a *pending* state. |
| 3 | **Employees directory** | Find | Server-side table (search, filter chips, sort, pagination of 1,284 results); band-position chips including part-time FTE (E9) and contractor "No band" (E10). |
| 4 | **Employee profile** | Understand | Full package breakdown (base, allowances shown monthly → annual, bonus as % of base), "How is this calculated?", one-time payment shown separately and excluded from total (E-rules), band gauge with compa-ratio, effective-dated history. |
| 5 | **Revise compensation** | Act → Confirm | **Interactive.** Promotion toggle applies L4 defaults (E3/E17), quick picks (+12%, band min, midpoint), live preview of before → after, % change, total pay and band position; a warning when still below band; bonus validation (E21); review → confirm → success with *pending until effective date* (E14). |
| 6 | **Exceptions** | Review | **Interactive tabs:** below band, above band (framed as informational), pending changes, missing package (E13). |
| 7 | **Insights** | Answer | **Interactive group-by** (country / department / level): range bars (min → max with median), fixed vs. variable mix, distribution against bands. |
| — | **Foundations** | — | Archetype, colour and status tokens, type scale, voice do/don't, principles. |

## Design decisions worth noting

- **Below band is amber, never red.** It's a prompt to review, not an error (Caregiver).
- **Status = colour + icon + text** (●/▼/▲/○), so it never depends on colour alone.
- **All amounts use Geist Mono with tabular figures**, so columns of money line up. Local currency formatting is respected (Indian lakh grouping for INR).
- **Preview before commit:** the revise screen catches that a 12% promotion raise still leaves Ravi below the L4 band minimum *before* anything is saved. This is the core product insight the backend's domain layer will compute.
- **The data is illustrative but internally consistent:** headcounts sum to 9,512 across every grouping, and exception counts add up to the sidebar badge (749).

## Mapping to implementation

Screens map 1:1 to Next.js routes (`/login`, `/`, `/employees`, `/employees/[id]`, `/employees/[id]/revise` as a full page, since the live preview needs the room, `/exceptions`, `/insights`). Tokens map to shadcn/ui CSS variables in `globals.css`.
