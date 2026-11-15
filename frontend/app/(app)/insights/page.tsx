"use client";

import { ArrowRightIcon, DownloadIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { FilterSelect } from "@/components/filter-select";
import { PageHeading, Panel } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BandChart, MixChart, PayHistogram } from "@/features/insights/charts";
import { exportUrl } from "@/lib/api";
import { EMPLOYMENT_TYPE_LABELS, formatCompactMoney, formatMoney, formatPercent } from "@/lib/format";
import {
  activeGroup,
  directoryHref,
  groupOptions,
  insightApiParams,
  insightFiltersFromParams,
  insightFiltersToParams,
  showsLocalCurrency,
  type GroupKey,
  type InsightFilters,
} from "@/lib/insight-filters";
import {
  useBandDistribution,
  useBreakdown,
  useCountries,
  useDepartments,
  usePayDistribution,
  useSummary,
} from "@/lib/queries";
import type { EmploymentType, PayGroup } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Levels read best in order (L1 to L5, then contractors); other groupings by median, highest first. */
function ordered(groups: PayGroup[], group: GroupKey): PayGroup[] {
  if (group !== "level") return groups;
  return [...groups].sort((a, b) => (a.key === "contractor" ? 1 : b.key === "contractor" ? -1 : a.key.localeCompare(b.key)));
}

function RangeTable({ groups, groupLabel }: { groups: PayGroup[]; groupLabel: string }) {
  const top = Math.max(...groups.map((g) => g.maximum.amount_minor), 1);
  const at = (amount: number) => `${(amount / top) * 100}%`;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th scope="col" className="py-2 font-medium">{groupLabel}</th>
            <th scope="col" className="py-2 text-right font-medium">Headcount</th>
            <th scope="col" className="w-1/2 px-6 py-2 font-medium">Range · min → max, with median</th>
            <th scope="col" className="py-2 text-right font-medium">Median</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.key} className="border-t border-muted">
              <th scope="row" className="py-3 text-left font-normal">{group.label}</th>
              <td className="amount py-3 text-right">{group.headcount.toLocaleString("en-US")}</td>
              <td className="px-6 py-3">
                <div
                  role="img"
                  aria-label={`${group.label}: from ${formatMoney(group.minimum)} to ${formatMoney(group.maximum)}, median ${formatMoney(group.median)}`}
                  className="relative h-5"
                >
                  <div
                    className="absolute top-1.5 h-2.5 rounded-full bg-[#C9CDEB]"
                    style={{ left: at(group.minimum.amount_minor), width: at(group.maximum.amount_minor - group.minimum.amount_minor) }}
                  />
                  <div className="absolute top-0.5 -ml-0.5 h-4.5 w-1 rounded-sm bg-primary" style={{ left: at(group.median.amount_minor) }} />
                </div>
              </td>
              <td className="amount py-3 text-right">{formatMoney(group.median)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly { key: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex gap-1 rounded-[10px] bg-muted p-1">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          aria-pressed={option.key === value}
          onClick={() => onChange(option.key)}
          className={cn(
            "h-8 rounded-lg px-3 text-[13px]",
            option.key === value ? "bg-card font-semibold text-foreground shadow-sm" : "text-subtle-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function InsightFilterBar({
  filters,
  localCurrency,
  onChange,
}: {
  filters: InsightFilters;
  localCurrency: string | undefined;
  onChange: (changes: Partial<InsightFilters>) => void;
}) {
  const countries = useCountries();
  const departments = useDepartments();
  const anyFilter = filters.country || filters.department || filters.level || filters.type;
  return (
    <section aria-label="Filters" className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-3">
      <FilterSelect
        label="Country"
        value={filters.country}
        onChange={(country) => onChange({ country })}
        options={(countries.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
      />
      <FilterSelect
        label="Department"
        value={filters.department}
        onChange={(department) => onChange({ department })}
        options={(departments.data ?? []).map((d) => ({ value: String(d.id), label: d.name }))}
      />
      <FilterSelect
        label="Level"
        value={filters.level}
        onChange={(level) => onChange({ level })}
        options={["1", "2", "3", "4", "5"].map((level) => ({ value: level, label: `L${level}` }))}
      />
      <FilterSelect
        label="Employment type"
        value={filters.type}
        onChange={(type) => onChange({ type })}
        options={(Object.keys(EMPLOYMENT_TYPE_LABELS) as EmploymentType[]).map((type) => ({
          value: type,
          label: EMPLOYMENT_TYPE_LABELS[type],
        }))}
      />
      {anyFilter ? (
        <button
          type="button"
          onClick={() => onChange({ country: "", department: "", level: "", type: "" })}
          className="h-9 px-2 text-[13px] text-primary underline"
        >
          Clear
        </button>
      ) : null}
      {filters.country && localCurrency && localCurrency !== "USD" ? (
        <div className="ml-auto">
          <Segmented
            label="Currency"
            value={filters.currency}
            onChange={(currency) => onChange({ currency })}
            options={[
              { key: "local", label: localCurrency },
              { key: "usd", label: "USD" },
            ]}
          />
        </div>
      ) : null}
    </section>
  );
}

function KpiCard({ label, value, children }: { label: string; value: string | undefined; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border bg-card p-5">
      <span className="text-[13px] text-muted-foreground">{label}</span>
      {value === undefined ? (
        <Skeleton className="h-9 w-28" />
      ) : (
        <span className="amount text-[28px] leading-tight font-medium tracking-tight">{value}</span>
      )}
      {children}
    </div>
  );
}

function InsightsView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filters = insightFiltersFromParams(new URLSearchParams(params.toString()));
  const countries = useCountries();
  const localCurrency = countries.data?.find((c) => c.code === filters.country)?.currency;
  const api = insightApiParams(filters).toString();
  const group = activeGroup(filters);
  const options = groupOptions(filters);
  const groupLabel = options.find((o) => o.key === group)?.label ?? "";

  const summary = useSummary(api);
  const distribution = usePayDistribution(api);
  const breakdown = useBreakdown(group ?? "country", api);
  const bands = useBandDistribution(group ?? "department", api);

  const update = (changes: Partial<InsightFilters>) => {
    const next = insightFiltersToParams({ ...filters, ...changes }).toString();
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false });
  };

  const exportParams = new URLSearchParams(api);
  exportParams.delete("currency");
  const data = summary.data;
  const currencyNote = showsLocalCurrency(filters) && localCurrency ? `in ${localCurrency}` : "in USD at reference rates";
  const narrowed = filters.country || filters.department || filters.level || filters.type;

  return (
    <>
      <PageHeading
        title="How ACME pays people"
        actions={
          <Button variant="outline" asChild className="h-10 bg-card px-3.5">
            <a href={exportUrl(exportParams)} download className="text-foreground hover:text-foreground">
              <DownloadIcon aria-hidden="true" />
              Export CSV
            </a>
          </Button>
        }
      >
        Narrow to a country, department, level or employment type to see its pattern. Active employees, total target
        pay {currencyNote}.
      </PageHeading>

      <InsightFilterBar filters={filters} localCurrency={localCurrency} onChange={update} />

      {summary.isError ? <ErrorState error={summary.error} onRetry={() => summary.refetch()} /> : null}

      <section
        aria-label="Key figures for this selection"
        className={cn("grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4", summary.isPlaceholderData && "opacity-60")}
      >
        <KpiCard label="Active headcount" value={data?.headcount.toLocaleString("en-US")}>
          {data ? (
            <span className="text-xs text-muted-foreground">
              +{data.joiners_this_quarter} joiners, −{data.leavers_this_quarter} leavers this quarter
            </span>
          ) : null}
        </KpiCard>
        <KpiCard label="Median total pay" value={data ? (data.median_pay ? formatMoney(data.median_pay) : "—") : undefined} />
        <KpiCard label="Total annual pay (target)" value={data ? formatCompactMoney(data.total_pay) : undefined}>
          {data ? (
            <span className="text-xs text-muted-foreground">Variable share {formatPercent(data.variable_share_percent)}</span>
          ) : null}
        </KpiCard>
        <KpiCard label="Paid within band" value={data ? formatPercent(data.paid_within_band_percent) : undefined}>
          {data ? (
            <span className="text-xs text-muted-foreground">Bonus eligible {formatPercent(data.bonus_eligible_percent)}</span>
          ) : null}
        </KpiCard>
      </section>

      {data && narrowed ? (
        <p className="-mt-2 text-sm">
          <Link href={directoryHref(filters)} className="inline-flex items-center gap-1">
            {/* No count here: the directory also lists people who haven't started yet. */}
            See these employees in the directory
            <ArrowRightIcon aria-hidden="true" className="size-3.5" />
          </Link>
        </p>
      ) : null}

      <Panel title="Pay distribution" id="distribution" aside="People by total target pay">
        {distribution.isError ? (
          <ErrorState error={distribution.error} onRetry={() => distribution.refetch()} />
        ) : !distribution.data ? (
          <LoadingRows rows={6} />
        ) : distribution.data.buckets.length === 0 ? (
          <EmptyState title="No pay recorded for this selection" />
        ) : (
          <div className={cn(distribution.isPlaceholderData && "opacity-60")}>
            <PayHistogram buckets={distribution.data.buckets} />
          </div>
        )}
      </Panel>

      {group === null ? (
        <EmptyState title="Nothing left to compare">
          Every grouping is narrowed to one value. Clear a country, department or level filter to compare groups.
        </EmptyState>
      ) : (
        <>
          <Panel
            title={`Total pay by ${groupLabel.toLowerCase()}`}
            id="by-group"
            aside={
              options.length > 1 ? (
                <Segmented label="Group by" value={group} options={options} onChange={(next) => update({ group: next })} />
              ) : null
            }
          >
            {breakdown.isError ? (
              <ErrorState error={breakdown.error} onRetry={() => breakdown.refetch()} />
            ) : !breakdown.data ? (
              <LoadingRows rows={8} />
            ) : breakdown.data.length === 0 ? (
              <EmptyState title="No pay recorded for this selection" />
            ) : (
              <div className={cn(breakdown.isPlaceholderData && "opacity-60")}>
                <RangeTable groups={ordered(breakdown.data, group)} groupLabel={groupLabel} />
              </div>
            )}
          </Panel>

          <div className="grid grid-cols-[repeat(auto-fit,minmax(420px,1fr))] gap-4">
            <Panel title="Fixed vs. variable pay" id="mix" aside={`Share of total target pay, by ${groupLabel.toLowerCase()}`}>
              {breakdown.isError ? (
                <ErrorState error={breakdown.error} onRetry={() => breakdown.refetch()} />
              ) : !breakdown.data ? (
                <LoadingRows rows={6} />
              ) : breakdown.data.length === 0 ? (
                <EmptyState title="No pay recorded for this selection" />
              ) : (
                <MixChart groups={ordered(breakdown.data, group)} />
              )}
            </Panel>
            <Panel title="Position against pay bands" id="bands" aside={<Link href="/exceptions">See exceptions</Link>}>
              {bands.isError ? (
                <ErrorState error={bands.error} onRetry={() => bands.refetch()} />
              ) : !bands.data ? (
                <LoadingRows rows={6} />
              ) : bands.data.length === 0 ? (
                <EmptyState title="No banded employees in this selection" />
              ) : (
                <>
                  <BandChart groups={bands.data} />
                  <p className="text-xs text-muted-foreground">
                    In band overall: {formatPercent(data?.paid_within_band_percent ?? null)}. Contractors aren&apos;t
                    banded and are left out.
                  </p>
                </>
              )}
            </Panel>
          </div>
        </>
      )}
    </>
  );
}

export default function InsightsPage() {
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <InsightsView />
    </Suspense>
  );
}
