import { Panel } from "@/components/page-heading";
import { formatDate, formatMoney } from "@/lib/format";
import type { EmployeeProfile, Package, PayComponent, RoleDefault } from "@/lib/types";
import { cn } from "@/lib/utils";

function componentNote(component: PayComponent, defaults: RoleDefault[]): string | null {
  if (component.frequency === "monthly" && component.amount) {
    return `${formatMoney(component.amount)} / month`;
  }
  if (component.percent !== null) {
    const isDefault = defaults.some(
      (d) => d.type === component.type && Number(d.percent) === Number(component.percent),
    );
    return `target ${Number(component.percent)}% of base${isDefault ? " · role default" : ""}`;
  }
  return null;
}

function Row({
  label,
  note,
  value,
  strong = false,
  indent = false,
}: {
  label: string;
  note?: string | null;
  value: string;
  strong?: boolean;
  indent?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex justify-between gap-4 border-b border-muted py-2.5",
        indent && "pl-4 text-subtle-foreground",
      )}
    >
      <dt className={cn(strong && "font-medium")}>
        {label}
        {note ? <span className="text-muted-foreground"> · {note}</span> : null}
      </dt>
      <dd className="amount">{value}</dd>
    </div>
  );
}

export function PackagePanel({
  profile,
  pkg,
  defaults,
}: {
  profile: EmployeeProfile;
  pkg: Package;
  defaults: RoleDefault[];
}) {
  const allowances = pkg.components.filter((c) => c.type === "allowance");
  const variable = pkg.components.filter((c) => c.type === "bonus" || c.type === "commission");
  const variableShare = Number(pkg.variable_share);

  return (
    <Panel
      title="Salary package"
      id="package"
      aside={`Since ${formatDate(pkg.effective_from)} · annual`}
    >
      <dl className="flex flex-col text-sm">
        <Row label="Base salary" value={formatMoney(pkg.base_salary)} strong />
        {allowances.map((c) => (
          <Row
            key={c.label}
            label={c.label}
            note={componentNote(c, defaults)}
            value={formatMoney(c.annual_amount)}
            indent
          />
        ))}
        <Row label="Fixed cash" value={formatMoney(pkg.fixed_cash)} strong />
        {variable.map((c) => (
          <Row
            key={c.label}
            label={c.label}
            note={componentNote(c, defaults)}
            value={formatMoney(c.annual_amount)}
            indent
          />
        ))}
        <div className="flex items-baseline justify-between gap-4 pt-3.5 pb-1">
          <dt className="font-semibold">Total target pay</dt>
          <dd className="flex flex-col items-end gap-0.5">
            <span className="amount text-xl font-medium">
              {formatMoney(pkg.total_target_compensation)}
            </span>
            <span className="amount text-xs text-muted-foreground">
              ≈ {formatMoney(pkg.total_target_compensation_usd)} at reference rate
            </span>
          </dd>
        </div>
      </dl>

      <div className="flex flex-col gap-1.5">
        <div aria-hidden="true" className="flex h-2 overflow-hidden rounded-full">
          <div className="bg-primary" style={{ width: `${100 - variableShare}%` }} />
          <div className="bg-primary-soft" style={{ width: `${variableShare}%` }} />
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Fixed {Math.round(100 - variableShare)}%</span>
          <span>Variable {Math.round(variableShare)}%</span>
        </div>
      </div>

      <details className="text-[13px] text-subtle-foreground">
        <summary className="cursor-pointer text-primary">How is this calculated?</summary>
        <p className="mt-2 leading-relaxed">
          Total target pay = base + recurring allowances (monthly × 12) + target bonus and
          commission. One-time payments, like a sign-on bonus, are shown separately and never
          included.
        </p>
      </details>

      {profile.one_time_payments.map((payment) => (
        <div
          key={`${payment.label}-${payment.payout_date}`}
          className="flex justify-between gap-4 rounded-lg bg-background px-3 py-2.5 text-[13px] text-subtle-foreground"
        >
          <span>
            One-time · {payment.label} · paid {formatDate(payment.payout_date)}
          </span>
          <span className="amount">{formatMoney(payment.amount)}</span>
        </div>
      ))}
    </Panel>
  );
}
