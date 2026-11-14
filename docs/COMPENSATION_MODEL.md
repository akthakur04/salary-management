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
                └──< CompensationVersion   (effective_from, effective_to?, reason, role, country)
                          ├── base_salary_annual  (money)
                          └──< CompensationComponent
                                 type:  ALLOWANCE | BONUS | COMMISSION | ONE_TIME
                                 basis: FIXED_AMOUNT | PERCENT_OF_BASE
                                 value, frequency (MONTHLY | ANNUAL | ONCE), payout_date?
```

| Concept | Meaning |
|---|---|
| **Role** | Job family + level, e.g. *Account Executive L2*. Determines the pay band and default structure. |
| **RoleDefaultComponent** | Template components applied when an employee is hired into a role. They are copied, not linked, so per-employee overrides are independent. Defaults are a **bonus or commission as a percentage of base**, because a role spans every country and currency; fixed amounts such as allowances are set per employee. |
| **CompensationVersion** | An immutable snapshot of an employee's package from a given date. A change creates a new version and closes the previous one. Each version records the **role and country** it applies to, so a future-dated promotion or transfer moves the employee to the new band only from its effective date. The first version is always the hire. |
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
| Band position | `below` if < min, `above` if > max, else `in_band` (min and max are inside the band); `no_band` for contractors or a role with no band in the country |

Rounding: calculate in minor units and round half-to-even once, at the end. Compa-ratio is shown to two decimal places, and percentages (raise %, variable share) to one.

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
| E11 | Terminated employee | Kept for history; excluded from headcount and current cost by default; filterable. The termination date is the **last day worked** and may be in the future: the employee counts as terminated from the day after, worked out at read time. Pay changes dated after the last day are rejected. |
| E12 | On leave | Counted in headcount and cost (still employed). |
| E13 | Employee with no compensation record | Shown in the Exceptions view; excluded from averages rather than counted as 0. |

### Time & history
| # | Case | Expected behaviour |
|---|---|---|
| E14 | Raise with a future effective date | Current package is unchanged until that date. Every future version shows as pending on the profile; the Exceptions view and the sidebar badge list those due in the next 60 days. |
| E15 | Backdated correction | Allowed with reason `correction` when dated on or after the start of the latest version. On that version's own start date it supersedes it, and the superseded version stays in history with a zero-length period. A correction dated between two existing versions is **rejected** with `OVERLAPPING_VERSION`, because earlier periods are kept as recorded. |
| E16 | Overlapping effective periods | **Rejected** by the domain layer. |
| E17 | Promotion (role change + raise) | New version under the new role; the band comparison switches to the new band. |
| E18 | Transfer to another country | New version with reason `transfer`, in the new country's currency; history keeps the old currency figures as they were. |
| E19 | Raise % between versions | Calculated in local currency (not USD) so FX doesn't distort it. |

### Validation
| # | Case | Expected behaviour |
|---|---|---|
| E20 | Zero or negative base / component | Rejected. |
| E21 | Bonus % outside 0–100 | Rejected. A 0% bonus is also rejected (E20): remove the bonus component instead. |
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

## 5. Edge-case traceability

Every edge case has at least one named test. Domain tests are in [`backend/tests/domain/`](../backend/tests/domain/) and run without a database.

| # | Case | Test(s) |
|---|---|---|
| E1 | Same role, different bases | `test_bands.py::test_two_employees_in_the_same_role_each_get_their_own_compa_ratio`, `test_package.py::test_two_employees_in_the_same_role_can_have_different_bases` |
| E2 | One bonus-eligible, one not | `test_package.py::test_employee_without_a_bonus_has_zero_target_variable` |
| E3 | Override a role default | `test_role_defaults.py::test_employee_can_override_a_role_default_without_changing_the_role`, `test_role_defaults.py::test_employee_can_have_a_role_default_removed` |
| E4 | Role default changes later | `test_role_defaults.py::test_changing_a_role_default_does_not_change_existing_employees` |
| E5 | No variable pay | `test_package.py::test_package_without_variable_pay_has_total_equal_to_fixed_cash` |
| E6 | Multiple allowances | `test_package.py::test_multiple_allowances_are_each_annualised_and_summed`, `test_components.py::test_monthly_allowance_is_annualised_by_twelve` |
| E7 | Fixed vs. % bonus | `test_package.py::test_fixed_and_percentage_bonuses_are_both_supported`, `test_package.py::test_percentage_bonus_recalculates_when_base_changes` |
| E8 | Sales commission | `test_package.py::test_sales_commission_counts_as_target_variable`, `test_package.py::test_fixed_and_variable_mix_shows_commission_as_variable` |
| E9 | Part-time | `test_bands.py::test_part_time_employee_is_compared_to_band_at_fte`, `test_bands.py::test_part_time_pay_that_looks_low_is_in_band_at_fte` |
| E10 | Contractor | `test_bands.py::test_contractor_has_no_band_and_no_compa_ratio`, `test_stats.py::test_contractors_are_excluded_from_band_distribution` |
| E11 | Terminated | `test_employment.py::test_terminated_employee_is_excluded_from_headcount_and_current_cost`, `test_employment.py::test_employee_is_terminated_from_the_day_after_their_last_day` |
| E12 | On leave | `test_employment.py::test_employee_on_leave_is_counted_in_headcount_and_cost` |
| E13 | No compensation record | `test_stats.py::test_employee_without_a_package_is_excluded_from_averages_not_counted_as_zero` |
| E14 | Future-dated raise | `test_versions.py::test_future_dated_raise_leaves_current_package_unchanged_until_its_date`, `test_versions.py::test_future_dated_raise_is_listed_as_pending`, `test_versions.py::test_only_changes_within_the_window_are_due_soon` |
| E15 | Backdated correction | `test_versions.py::test_backdated_correction_after_the_latest_version_is_allowed`, `test_versions.py::test_correction_on_the_latest_version_date_replaces_it_and_keeps_it_in_history`, `test_versions.py::test_correction_dated_between_two_existing_versions_is_rejected` |
| E16 | Overlapping periods | `test_versions.py::test_overlapping_effective_periods_are_rejected`, `test_versions.py::test_history_with_two_open_versions_is_rejected`, `test_versions.py::test_change_dated_before_a_pending_change_is_rejected` |
| E17 | Promotion | `test_versions.py::test_promotion_moves_the_employee_to_the_new_role_from_its_effective_date` |
| E18 | Transfer to another country | `test_versions.py::test_transfer_starts_a_version_in_the_new_currency_and_keeps_old_figures` |
| E19 | Raise % in local currency | `test_versions.py::test_raise_percentage_is_calculated_in_local_currency`, `test_versions.py::test_raise_percentage_is_not_reported_across_a_currency_change` |
| E20 | Zero or negative amount | `test_package.py::test_zero_or_negative_base_salary_is_rejected`, `test_components.py::test_zero_or_negative_component_amount_is_rejected` |
| E21 | Bonus % outside 0–100 | `test_components.py::test_bonus_percentage_outside_0_to_100_is_rejected`, `test_components.py::test_commission_percentage_outside_0_to_100_is_rejected` |
| E22 | Currency doesn't match country | `test_versions.py::test_currency_that_does_not_match_the_country_is_rejected`, `test_package.py::test_component_in_a_different_currency_from_base_is_rejected` |
| E23 | One-time payment without date | `test_components.py::test_one_time_payment_without_payout_date_is_rejected` |
| E24 | Duplicate code or email | `test_identity.py::test_duplicate_employee_code_is_rejected`, `test_identity.py::test_duplicate_email_is_rejected_ignoring_case` |
| E25 | Missing FX rate | `test_fx.py::test_missing_fx_rate_fails_loudly_instead_of_returning_zero`, `test_fx.py::test_rate_set_must_cover_every_currency_in_use` |

Later phases add tests where an edge case also needs the database or the API: unique indexes (E24) and one open version per employee (E16) in Phase 3; contractors counted in cost (E10), terminated employees excluded by default (E11), and missing packages listed in Exceptions (E13) in Phase 5.
