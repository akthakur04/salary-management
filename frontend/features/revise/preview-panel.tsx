import { TriangleAlertIcon } from "lucide-react";

import { BandGauge } from "@/components/band-gauge";
import { Panel } from "@/components/page-heading";
import { Skeleton } from "@/components/ui/skeleton";
import { formatChange, formatMoney } from "@/lib/format";
import type { Preview } from "@/lib/types";
import { cn } from "@/lib/utils";

function Line({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-muted py-2.5">
      <dt>{label}</dt>
      <dd className={cn("amount", tone)}>{value}</dd>
    </div>
  );
}

/**
 * Preview before commit: everything here comes from the server's dry run, the
 * same calculation and checks a save would run, so it can't drift from what's saved.
 */
export function PreviewPanel({
  preview,
  error,
  loading,
  countryName,
  children,
}: {
  preview: Preview | undefined;
  error: string | null;
  loading: boolean;
  countryName: string;
  children: React.ReactNode;
}) {
  const after = preview?.after;
  const before = preview?.before;
  const band = after?.band;
  const allowances = after
    ? { ...after.fixed_cash, amount_minor: after.fixed_cash.amount_minor - after.base_salary.amount_minor }
    : null;

  return (
    <Panel title="Preview" id="preview" aside="Nothing is saved yet">
      {error ? (
        <p role="alert" className="rounded-[10px] bg-rose-tint px-3.5 py-3 text-[13px] text-rose-text">
          {error}
        </p>
      ) : null}
      {!after ? (
        <div className="flex flex-col gap-3" aria-busy="true">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <div className={cn("flex flex-col gap-4 transition-opacity", loading && "opacity-60")} aria-live="polite">
          <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
            <div className="flex flex-col gap-1 rounded-[10px] bg-background p-3.5">
              <span className="text-xs text-muted-foreground">Base today</span>
              <span className="amount text-lg">{before ? formatMoney(before.base_salary) : "—"}</span>
            </div>
            <span aria-hidden="true" className="text-muted-foreground">
              →
            </span>
            <div className="flex flex-col gap-1 rounded-[10px] bg-primary-tint p-3.5">
              <span className="text-xs text-primary-strong">New base</span>
              <span className="amount text-lg">{formatMoney(after.base_salary)}</span>
            </div>
          </div>

          <dl className="flex flex-col text-sm">
            <Line
              label="Change in base"
              value={formatChange(preview.base_change_percent)}
              tone={Number(preview.base_change_percent) >= 0 ? "text-sage-text" : "text-muted-foreground"}
            />
            <Line label="Target variable pay" value={formatMoney(after.target_variable)} />
            {allowances && allowances.amount_minor > 0 ? (
              <Line label="Allowances" value={formatMoney(allowances)} />
            ) : null}
            <div className="flex items-baseline justify-between gap-4 pt-3">
              <dt className="font-semibold">Total target pay</dt>
              <dd className="flex flex-col items-end gap-0.5">
                <span className="amount text-xl">{formatMoney(after.total_target_compensation)}</span>
                <span className="amount text-xs text-muted-foreground">
                  {before ? `was ${formatMoney(before.total_target_compensation)} · ` : ""}≈{" "}
                  {formatMoney(after.total_target_compensation_usd)}
                </span>
              </dd>
            </div>
          </dl>

          {band?.band ? (
            <div className="flex flex-col gap-2.5 border-t border-muted pt-2">
              <div className="flex items-baseline justify-between gap-4">
                <span className="text-sm font-medium">
                  {after.role.title} L{after.role.level} · {countryName} band
                </span>
                <span className="amount text-sm">compa-ratio {band.compa_ratio}</span>
              </div>
              <BandGauge band={band.band} value={band.fte_equivalent_base} position={band.position} />
            </div>
          ) : null}

          {band?.position === "below" && band.band ? (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-[10px] border border-amber-line bg-amber-surface px-3.5 py-3 text-[13px] leading-normal text-[#5E3D05]"
            >
              <TriangleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-amber-text" />
              <span>
                <b>Still below the band minimum.</b> The new base is{" "}
                {band.gap_to_minimum ? formatMoney(band.gap_to_minimum) : ""} short of the minimum (
                {formatMoney(band.band.minimum)}). You can save it, but it will show in Exceptions.
              </span>
            </div>
          ) : band?.position === "above" ? (
            <p role="status" className="rounded-[10px] bg-violet-tint px-3.5 py-3 text-[13px] text-violet-text">
              <span aria-hidden="true">▲ </span>Above the band maximum after this change. Worth
              confirming it&apos;s deliberate.
            </p>
          ) : band?.position === "in_band" ? (
            <p role="status" className="rounded-[10px] border border-[#CFE0D5] bg-[#EEF5F0] px-3.5 py-3 text-[13px] text-[#2C4D3A]">
              <span aria-hidden="true">● </span>Within band after this change.
            </p>
          ) : null}
        </div>
      )}
      {children}
    </Panel>
  );
}
