/**
 * Types mirroring the API's response models (backend/app/schemas). Money is
 * minor units plus a currency; decimals arrive as fixed-precision strings.
 */

export type Money = { amount_minor: number; currency: string };

export type BandPosition = "below" | "in_band" | "above" | "no_band";
export type EmploymentType = "full_time" | "part_time" | "contractor";
export type EmploymentStatus = "active" | "on_leave" | "terminated";
export type ChangeReason =
  | "hire"
  | "promotion"
  | "merit"
  | "market_adjustment"
  | "transfer"
  | "correction";
export type ComponentType = "allowance" | "bonus" | "commission" | "one_time";
export type ComponentBasis = "fixed_amount" | "percent_of_base";
export type Frequency = "monthly" | "annual" | "once";
export type VersionState = "current" | "pending" | "past" | "superseded";

export type RoleRef = { id: number; title: string; level: number };
export type CountryRef = { code: string; name: string };

export type BandComparison = {
  position: BandPosition;
  compa_ratio: string | null;
  fte_equivalent_base: Money;
  gap_to_minimum: Money | null;
};

export type BandRange = { minimum: Money; midpoint: Money; maximum: Money };
export type Band = BandComparison & { band: BandRange | null };

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type EmployeeSummary = {
  id: number;
  employee_code: string;
  name: string;
  email: string;
  role: RoleRef | null;
  department: string | null;
  country: CountryRef | null;
  employment_type: EmploymentType;
  fte: string;
  status: EmploymentStatus;
  base_salary: Money | null;
  total_pay: Money | null;
  total_pay_usd: Money | null;
  band: BandComparison | null;
  last_change: string | null;
};

export type PayComponent = {
  type: ComponentType;
  basis: ComponentBasis;
  frequency: Frequency;
  label: string;
  amount: Money | null;
  percent: string | null;
  payout_date: string | null;
  annual_amount: Money;
};

export type Package = {
  version_id: number;
  effective_from: string;
  reason: ChangeReason;
  base_salary: Money;
  components: PayComponent[];
  fixed_cash: Money;
  target_variable: Money;
  total_target_compensation: Money;
  total_target_compensation_usd: Money;
  variable_share: string;
};

export type HistoryEntry = {
  version_id: number;
  effective_from: string;
  effective_to: string | null;
  state: VersionState;
  reason: ChangeReason;
  role: RoleRef;
  country_code: string;
  base_salary: Money;
  components: PayComponent[];
  fixed_cash: Money;
  target_variable: Money;
  total_target_compensation: Money;
  base_change_percent: string | null;
  note: string | null;
};

export type EmployeeProfile = {
  id: number;
  employee_code: string;
  name: string;
  email: string;
  employment_type: EmploymentType;
  fte: string;
  status: EmploymentStatus;
  hire_date: string;
  termination_date: string | null;
  role: (RoleRef & { family: string; department: string }) | null;
  country: CountryRef | null;
  currency: string | null;
  package: Package | null;
  band: Band | null;
  peers: { count: number; median_base: Money | null };
  pending_changes: HistoryEntry[];
  one_time_payments: { label: string; amount: Money; payout_date: string }[];
};

export type PreviewSide = {
  role: RoleRef;
  country_code: string;
  base_salary: Money;
  fixed_cash: Money;
  target_variable: Money;
  total_target_compensation: Money;
  total_target_compensation_usd: Money;
  band: Band;
};

export type Preview = {
  before: PreviewSide | null;
  after: PreviewSide;
  base_change_percent: string | null;
  takes_effect_later: boolean;
};

export type Summary = {
  as_of: string;
  headcount: number;
  joiners_this_quarter: number;
  leavers_this_quarter: number;
  total_pay_usd: Money;
  median_pay_usd: Money | null;
  paid_within_band_percent: string | null;
  bonus_eligible_percent: string | null;
  variable_share_percent: string | null;
  employees_without_package: number;
};

export type PayGroup = {
  key: string;
  label: string;
  headcount: number;
  minimum: Money;
  median: Money;
  mean: Money;
  maximum: Money;
  variable_share_percent: string | null;
};

export type BandGroup = {
  key: string;
  label: string;
  below: number;
  in_band: number;
  above: number;
  banded: number;
  in_band_percent: string | null;
};

export type ExceptionType = "below" | "above" | "pending" | "missing";

export type ExceptionItem = {
  employee_id: number;
  employee_code: string;
  name: string;
  role: RoleRef | null;
  country_code: string | null;
  base_salary: Money | null;
  band_minimum: Money | null;
  band_maximum: Money | null;
  gap: Money | null;
  gap_percent: string | null;
  new_base_salary: Money | null;
  effective_from: string | null;
  reason: ChangeReason | null;
};

export type ExceptionCounts = {
  below: number;
  above: number;
  pending: number;
  missing: number;
  total: number;
};

export type Exceptions = Page<ExceptionItem> & { counts: ExceptionCounts; type: ExceptionType };

export type RecentChange = {
  employee_id: number;
  name: string;
  role: RoleRef;
  country_code: string;
  reason: ChangeReason;
  effective_from: string;
  is_pending: boolean;
  base_change_percent: string | null;
};

export type Country = { code: string; name: string; currency: string };
export type Department = { id: number; name: string };
export type RoleDefault = { type: ComponentType; percent: string; label: string };
export type Role = {
  id: number;
  department_id: number;
  department: string;
  family: string;
  level: number;
  title: string;
  defaults: RoleDefault[];
};
export type PayBandListing = BandRange & { role_id: number; country_code: string };

export type ApiErrorBody = {
  error: { code: string; message: string; details: Record<string, unknown> };
};

export type ComponentInput = {
  type: ComponentType;
  basis: ComponentBasis;
  frequency: Frequency;
  label: string;
  amount_minor?: number;
  percent?: string;
  payout_date?: string;
};
