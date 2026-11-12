# Compensation Model & Edge Cases

Companion to [REQUIREMENTS.md](REQUIREMENTS.md). This doc defines **how compensation is represented and calculated**, and lists the edge cases the system must handle. Each edge case becomes one or more unit tests.

## 1. Domain model (conceptual)

```
Country ──< Employee >── Role (job family + level) >── Department
   │            │              │
   │            │              └──< RoleDefaultComponent   (template)
   │            │
   └──< PayBand (role × country: min / mid / max)
                │
                └──< CompensationVersion   (effective_from, effective_to?, reason)
                          ├── base_salary_annual  (money)
                          └──< CompensationComponent
                                 type:  ALLOWANCE | BONUS | COMMISSION | ONE_TIME
                                 basis: FIXED_AMOUNT | PERCENT_OF_BASE
                                 value, frequency (MONTHLY | ANNUAL | ONCE), payout_date?
```

| Concept | Meaning |
|---|---|
| **Role** | Job family + level, e.g. *Account Executive L2*. Determines the pay band and default structure. |
| **RoleDefaultComponent** | Template components applied when an employee is hired into a role. They are copied, not linked, so per-employee overrides are independent. |
| **CompensationVersion** | An immutable snapshot of an employee's package from a given date. A change creates a new version and closes the previous one. |
| **Component** | One element of pay. Its *type* says what it is; its *basis* says how it's calculated. |
| **Money** | `(amount_minor: int, currency: ISO-4217)`. Never a float. |

## 2. Calculation rules

All figures are **annual** and in the employee's **local currency**, then converted to USD with the reference rate.

| Metric | Formula |
|---|---|
| Annual base | `base_salary_annual` |
| Fixed cash | base + Σ recurring allowances (monthly × 12) |
| Target variable | Σ BONUS + Σ COMMISSION (percent → `pct × base`) |
| **Total target compensation (TTC)** | fixed cash + target variable |
| One-time payments | Reported separately for the year of `payout_date`; **never** included in TTC |
| FTE-equivalent base | base ÷ FTE (used only for band comparison) |
| Compa-ratio | FTE-equivalent base ÷ band midpoint |
| Band position | `below` if < min, `above` if > max, else `in_band` |

Rounding: calculate in minor units and round half-to-even once, at the end.

## 3. Edge cases

### Structure variations
| # | Case | Expected behaviour |
|---|---|---|
| E1 | Two employees, same role, different bases | Both valid; each has its own compa-ratio. |
| E2 | Same role; one bonus-eligible, one not | Bonus component is present on one and absent on the other; target variable is 0 for the latter. |
| E3 | Employee overrides a role default (e.g. 20% bonus instead of 15%) | Override stored on the employee's version; role template unchanged. |
| E4 | Role default changes later | Existing employees are **not** changed retroactively; only new hires get the new default. |
| E5 | Employee has no variable pay at all | TTC = fixed cash. |
| E6 | Multiple allowances (housing + transport) | Each annualised and summed. |
| E7 | Bonus as fixed amount vs. % of base | Both supported; % recalculates when base changes. |
| E8 | Sales commission (OTE) | Counts as target variable; the fixed/variable mix shows this clearly. |

### Employment type & status
| # | Case | Expected behaviour |
|---|---|---|
| E9 | Part-time (e.g. 60% FTE) | Pay stored as actually paid; band comparison uses FTE-equivalent. |
| E10 | Contractor | Has compensation but **no pay band** (compa-ratio "n/a"); excluded from band analytics, included in cost. |
| E11 | Terminated employee | Kept for history; excluded from headcount and current cost by default; filterable. |
| E12 | On leave | Counted in headcount and cost (still employed). |
| E13 | Employee with no compensation record | Shown in the Exceptions view; excluded from averages rather than counted as 0. |

### Time & history
| # | Case | Expected behaviour |
|---|---|---|
| E14 | Raise with a future effective date | Current package is unchanged until that date; shown as "pending" in Exceptions. |
| E15 | Backdated correction | Allowed with reason `correction`; history shows it. |
| E16 | Overlapping effective periods | **Rejected** by the domain layer. |
| E17 | Promotion (role change + raise) | New version under the new role; the band comparison switches to the new band. |
| E18 | Transfer to another country | New version in the new currency; history keeps the old currency figures as they were. |
| E19 | Raise % between versions | Calculated in local currency (not USD) so FX doesn't distort it. |

### Validation
| # | Case | Expected behaviour |
|---|---|---|
| E20 | Zero or negative base / component | Rejected. |
| E21 | Bonus % outside 0–100 | Rejected. |
| E22 | Currency doesn't match the employee's country | Rejected (one currency per employee per version). |
| E23 | One-time payment without payout date | Rejected. |
| E24 | Duplicate employee code / email | Rejected. |
| E25 | Missing FX rate for a currency | Fails loudly at seed/config time, never silently returns 0. |

## 4. Seed data shape

The seed script (fixed random seed) produces:
- 10,000 employees across ~8 countries (US, UK, DE, IN, SG, BR, CA, AU), ~8 departments, ~25 roles × 5 levels.
- Pay bands per role level and country; ~85% of employees in band, the rest deliberately below or above.
- Role-based default structures, with ~20% of employees carrying overrides (E3).
- 1–4 compensation versions per employee (hire, merits, promotions), some future-dated (E14).
- A mix of employment types (~85% full-time, ~8% part-time, ~7% contractor) and statuses (~5% terminated).
