# ACME Salary Management — Requirements

**Persona:** HR Manager, ACME Org  ·  **Scale:** ~10,000 employees, 8+ countries, many roles
**Companion doc:** [COMPENSATION_MODEL.md](COMPENSATION_MODEL.md) covers the domain model, calculation rules, and edge cases.

## 1. Problem

ACME's HR team manages salary data for 10,000 employees across multiple countries in Excel. A spreadsheet row can't represent how ACME actually pays people:
- **Roles pay differently.** Sales staff earn commission, engineers get annual bonuses, and some locations pay housing allowances.
- **People in the same role are paid differently.** Two Senior Engineers in Germany may have different base pay, and only one of them may be bonus-eligible.
- **Pay changes over time** through promotions, merit raises, and corrections. Excel overwrites the old value and loses the history.
- **Nobody can tell whether pay is fair or consistent.** Is this person under-paid for their level? Which teams sit outside their pay bands?

## 2. Goal

Web-based **salary management** software where the HR Manager can **manage salary data** for all employees and **answer questions about how the org pays people**. This is the goal as stated in the brief.

**How we interpret "salary":** a single base-salary number can't answer "how does the org pay people?" when some employees get bonuses, commission, or allowances and others don't. So a salary here is the employee's **full salary package**: base pay plus its components, versioned over time. Pay bands, compa-ratio, and the exceptions view are our product additions on top of the brief, prioritised below so the core ships first.

**What this is not:** payroll processing (calculating tax and deductions and paying people each month). The brief doesn't ask for it; see §5.

**Success looks like:**
- Find any employee and see their full compensation package in < 3 seconds.
- Record a raise or promotion, with a reason and an effective date, in < 1 minute, and keep the history.
- Answer "who is paid below their band?", "what does Engineering cost us?", and "how much of our pay is variable?" from one screen.

## 3. In Scope — prioritised (MoSCoW)

### Must have (v1 core)
| # | Feature |
|---|---|
| M1 | **Job architecture:** departments, roles (job family + level, e.g. *Software Engineer L3*), countries with local currency. |
| M2 | **Employee directory:** server-side paginated list with search, sort, and filters (country, department, role, level, employment type, status). |
| M3 | **Employee profile:** personal and job details, employment type (full-time / part-time with FTE % / contractor), status (active / on leave / terminated). |
| M4 | **Compensation package per employee:** annual base salary plus any number of **components**: recurring allowances, target annual bonus (% of base or fixed amount), sales commission (target variable), one-time payments (sign-on, retention). Each employee can have a different mix. |
| M5 | **Role default structures:** each role defines its default components (e.g. Sales → commission; Engineering L4+ → 15% bonus). New hires get the defaults; HR can **override or remove them per employee**. |
| M6 | **Effective-dated history:** every compensation change creates a new version with an **effective date** and a **reason** (hire, promotion, merit, market adjustment, correction). History is never overwritten. Future-dated changes are supported. |
| M7 | **Total compensation calculation:** annual base, fixed cash, target variable, and total target compensation, in local currency **and** USD (fixed reference FX rates). |
| M8 | **Seed script:** 10,000 deterministic employees with realistic structures, histories, and edge cases. |

### Should have (v1, makes it a product)
| # | Feature |
|---|---|
| S1 | **Pay bands:** min / mid / max per role level per country. Each employee shows a **compa-ratio** (salary ÷ band midpoint) and an in-band / below / above flag. |
| S2 | **Insights dashboard:** headcount and total compensation cost; pay by country, department, and role level; fixed vs. variable mix; bonus-eligibility rate; distribution of employees against their bands. |
| S3 | **Exceptions view:** employees out of band, missing a compensation record, or with pending future-dated changes. These are the HR Manager's to-do list. |
| S4 | **CSV export** of any filtered employee list. This is the bridge off Excel. |

### Could have (stretch)
C1 Bulk CSV import with row-level validation report · C2 Annual merit-cycle planning (budget %, proposed raises) · C3 Single-user login.

## 4. Key Decisions & Assumptions

- **Everything is annualised.** Allowances can be entered monthly or annually but are stored and compared annually. One-time payments count toward the year they're paid in, never toward recurring compensation.
- **Bonus and commission are stored as *targets*.** Recording actual payouts belongs to payroll and performance systems.
- **Part-time pay is compared at full-time equivalent (FTE).** A 50% FTE employee on 40k is compared to the band as 80k.
- **Money is stored as integer minor units with a currency code**; no floats are used for money. FX conversion uses a fixed, versioned reference-rate table, so results are deterministic and testable.
- **Single persona, synthetic data.** No real PII.

## 5. Deliberately Out of Scope (and why)

| Left out | Why |
|---|---|
| **Payroll runs, tax, statutory deductions, payslips, bank disbursement** | Not in the brief, which asks for salary *data* management and pay insights. Every country also has its own tax and social-security rules; getting them wrong has legal consequences, and doing it properly for 8 countries is a separate product. |
| **Actual bonus/commission payouts, performance ratings** | These come from sales and performance systems. We store the *agreed target*, which is what pay decisions are made on. |
| **Equity / stock grants** | Valuation (vesting schedules, strike price, 409A-style valuations) is complex, and an approximate number would mislead. |
| **Benefits (insurance, pension contributions)** | Usually set by country-level plans, not per-employee decisions. |
| **Authentication / roles / approval workflows** | There's one persona. The data model records *reason* and *effective date* so an approval step can be added later without a schema change. |
| **Gender / pay-equity analytics** | Sensitive. It needs proper statistical controls and legal framing, and a naive version would mislead. |
| **Live FX rates** | Non-deterministic and an external dependency. Reference rates are standard practice for compensation comparison. |

## 6. Non-Functional Requirements

- **Performance:** list and insight endpoints < 300 ms at 10k employees and ~30k compensation versions (indexed filters, SQL aggregates, a precomputed "current package" view).
- **Correctness:** domain rules (no overlapping effective periods, positive amounts, valid currency) are enforced in a tested domain layer, not only in the UI.
- **Quality:** fast, deterministic unit tests around calculations and rules; incremental, test-first commits.
- **Usability:** a non-technical HR Manager can use it without training, with clear empty, loading, error, and confirmation states.
