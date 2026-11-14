import { formatChange, formatDate, formatMoney, majorToMinor, REASON_LABELS } from "@/lib/format";
import type { RevisionBody } from "@/lib/queries";
import type {
  ChangeReason,
  ComponentInput,
  ComponentType,
  Money,
  Package,
  Preview,
  Role,
  RoleRef,
} from "@/lib/types";

/** Pure logic for the revise page, kept out of the components so it can be tested directly. */


export function nextLevelRole(roles: Role[], current: RoleRef): Role | undefined {
  const family = roles.find((role) => role.id === current.id)?.family;
  return roles.find((role) => role.family === family && role.level === current.level + 1);
}

export function variableDefault(role: Role | undefined): { type: ComponentType; percent: string; label: string } | null {
  const variable = role?.defaults.find((d) => d.type === "bonus" || d.type === "commission");
  return variable ? { type: variable.type, percent: String(Number(variable.percent)), label: variable.label } : null;
}

/** A raise in whole local units, rounded to the nearest hundred. */
export function raiseBy(base: Money, percent: number): number {
  return Math.round((base.amount_minor / 100) * (1 + percent / 100) / 100) * 100;
}

export function revisionBody(
  values: { reason: ChangeReason; effectiveFrom: string; baseAnnual: number; bonusPercent: number | null; note: string },
  context: { pkg: Package | null; roleId: number | null; variable?: { type: ComponentType; label: string } },
): RevisionBody {
  const recurring = (context.pkg?.components ?? []).filter((c) => c.type !== "one_time");
  const fixed: ComponentInput[] = recurring
    .filter((c) => c.basis === "fixed_amount" && c.amount)
    .filter((c) => c.type === "allowance")
    .map((c) => ({
      type: c.type,
      basis: "fixed_amount",
      frequency: c.frequency,
      label: c.label,
      amount_minor: c.amount?.amount_minor,
    }));
  const currentVariable = recurring.find((c) => c.type === "bonus" || c.type === "commission");
  const kind = context.variable ?? {
    type: currentVariable?.type ?? "bonus",
    label: currentVariable?.label ?? "Annual bonus",
  };
  const variable: ComponentInput[] =
    values.bonusPercent && values.bonusPercent > 0
      ? [
          {
            type: kind.type,
            basis: "percent_of_base",
            frequency: "annual",
            label: kind.label,
            percent: String(values.bonusPercent),
          },
        ]
      : [];
  const note = values.note.trim();
  return {
    effective_from: values.effectiveFrom,
    reason: values.reason,
    base_annual_minor: majorToMinor(values.baseAnnual),
    ...(context.roleId !== null ? { role_id: context.roleId } : {}),
    components: [...fixed, ...variable],
    ...(note ? { note } : {}),
  };
}

export function confirmationSummary(
  preview: Preview,
  values: { reason: ChangeReason; effectiveFrom: string; bonusPercent: number | null },
  promoted: boolean,
): string {
  const after = preview.after;
  const headline = promoted
    ? `${REASON_LABELS[values.reason]} to ${after.role.title} L${after.role.level}`
    : REASON_LABELS[values.reason];
  const base = preview.before
    ? `Base ${formatMoney(preview.before.base_salary)} → ${formatMoney(after.base_salary)} (${formatChange(preview.base_change_percent)})`
    : `Base ${formatMoney(after.base_salary)}`;
  const bonus = values.bonusPercent ? `, bonus target ${values.bonusPercent}%` : "";
  const total = preview.before
    ? `Total target pay ${formatMoney(preview.before.total_target_compensation)} → ${formatMoney(after.total_target_compensation)}`
    : `Total target pay ${formatMoney(after.total_target_compensation)}`;
  return `${headline}, effective ${formatDate(values.effectiveFrom)}. ${base}${bonus}. ${total}. The current package stays in history.`;
}

export function defaultEffectiveDate(today: Date = new Date()): string {
  const year = today.getUTCMonth() === 11 ? today.getUTCFullYear() + 1 : today.getUTCFullYear();
  const month = (today.getUTCMonth() + 1) % 12;
  return `${year}-${String(month + 1).padStart(2, "0")}-01`;
}
