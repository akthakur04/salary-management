# Salary Management — Requirements

**Persona:** HR Manager, ACME Org  ·  **Scale:** ~10,000 employees across multiple countries

## 1. Problem

ACME's HR team keeps salary data for 10,000 employees in Excel spreadsheets. Updating them is tedious and error-prone. Simple questions such as *"What do we pay engineers in India vs. the US?"* mean manual pivot tables. Nothing validates the data, nothing is audited, and there's no single source of truth.

## 2. Goal

A web application where the HR Manager can:
1. **Manage** employee salary records reliably (find, add, update, remove).
2. **Understand** how the org pays people, with answers to common compensation questions in seconds instead of spreadsheet work.

**Success looks like:** an HR Manager finds any employee in under 3 seconds and updates their salary in under 30 seconds. They can answer *"how do we pay X across Y?"* from one screen without exporting to Excel.

## 3. In Scope (v1)

### A. Employee & salary management
| # | Feature | Notes |
|---|---|---|
| A1 | **Employee list** | Server-side pagination, sorting, and filtering by country, department, and job title; search by name or employee ID. Has to stay fast at 10k rows. |
| A2 | **View employee** | Profile: name, employee ID, job title, department, country, employment type, hire date, salary (local currency + USD equivalent). |
| A3 | **Add employee** | Form with validation (required fields, salary > 0, valid country/currency, unique employee ID). |
| A4 | **Edit employee / salary** | Update details and salary, with the same validation as A3. |
| A5 | **Delete employee** | Hard delete, behind a confirmation dialog. |

### B. Pay insights (*"how does the org pay people?"*)
| # | Question answered | Output |
|---|---|---|
| B1 | What is our total payroll and headcount? | Org-wide KPI cards (headcount, total annual payroll in USD, median salary). |
| B2 | How does pay differ by **country**? | Per country: headcount, min / median / mean / max salary. |
| B3 | How does pay differ by **department** and **job title**? | Same stats grouped by department or job title, filterable by country. |
| B4 | What does a given role pay in a given country? | Salary range (min / p25 / median / p75 / max) for a selected job title + country. |

All insights are computed **in the database** (SQL aggregates), not in the browser.

### C. Platform
- **Seed script** generating 10,000 realistic, deterministic employees (fixed random seed) across ~8 countries, departments, and job levels.
- **REST API** (Python / FastAPI) + **relational DB** (SQLite locally; swappable via config).
- **React UI** with a component library.
- **Unit and API tests** for validation, salary/currency logic, list filtering, and insight aggregation.
- **Deployed** and publicly reachable; short video demo.

## 4. Key Decisions & Assumptions

- **Currency:** salaries are stored in the employee's **local currency** (the source of truth). For cross-country comparison they're converted to **USD using a fixed, seeded exchange-rate table**. This keeps results deterministic and testable; the rates are labelled "reference rates" in the UI.
- **Annual base salary only.** One current salary per employee, as an annual gross figure.
- **Single persona, single tenant.** The HR Manager is the only user type.
- **Data is synthetic.** No real PII; seed data is safe to deploy publicly.

## 5. Deliberately Out of Scope (and why)

| Left out | Why |
|---|---|
| **Authentication & role-based access** | One persona, synthetic data. Auth adds plumbing without showing the core product. The design leaves room to add it later (API behind a single auth dependency). |
| **Salary history / audit trail** | Valuable (raise trends, compliance), but it doubles the data model. v1 shows *current* pay; history is the first v2 item. |
| **Bonuses, equity, allowances, benefits** | Total-comp modelling varies a lot by country. Base salary answers the core question. |
| **Payroll processing, tax, deductions** | Different product (payroll vs. compensation management) and heavily regulated per country. |
| **Live FX rates** | Makes results non-deterministic and adds an external dependency. Fixed reference rates are enough for comparison. |
| **Excel import / export** | The natural migration path off Excel, but the seed script stands in for import in v1. CSV export is the first stretch goal if time allows. |
| **Pay-equity analysis (gender, etc.)** | Sensitive. Doing it properly needs careful statistical and legal framing, and a half-built version could mislead. |
| **Org hierarchy / manager relationships, approvals workflow** | Not needed to manage or analyse salaries; adds significant UI and model complexity. |
| **Charts-heavy BI / custom report builder** | A few focused, high-value questions beat a generic dashboard builder. |

## 6. Non-Functional Requirements

- **Performance:** list and insight endpoints respond in < 300 ms at 10k employees (indexed filter columns, paginated queries, aggregates in SQL).
- **Correctness:** server-side validation is the source of truth; the UI mirrors it for fast feedback.
- **Quality:** tests are fast (in-memory/isolated DB), deterministic (fixed seed and FX rates), and readable. Incremental commits show how the solution evolved.
- **Usability:** usable on a laptop screen without training; clear empty, loading, and error states.

## 7. Stretch Goals (only if v1 is solid)

1. CSV export of the filtered employee list.
2. Salary history with a "last raise" view.
3. Basic auth (single HR login).
