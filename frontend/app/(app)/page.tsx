"use client";

import Link from "next/link";

import { PageHeading, Panel } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatChange,
  formatCompactUsd,
  formatDate,
  formatMoney,
  formatPercent,
  REASON_LABELS,
} from "@/lib/format";
import {
  useBandDistribution,
  useBreakdown,
  useCountries,
  useExceptions,
  useMe,
  useRecentChanges,
  useSummary,
} from "@/lib/queries";
import type { ExceptionCounts, ExceptionType } from "@/lib/types";
import { cn } from "@/lib/utils";

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

function KpiCard({
  label,
  value,
  children,
}: {
  label: string;
  value: string | undefined;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border bg-card p-5">
      <span className="text-[13px] text-muted-foreground">{label}</span>
      {value === undefined ? (
        <Skeleton className="h-10 w-32" />
      ) : (
        <span className="amount text-[32px] leading-tight font-medium tracking-tight">{value}</span>
      )}
      {children}
    </div>
  );
}

function BandMix() {
  const bands = useBandDistribution("department");
  if (!bands.data) return <Skeleton className="h-1.5 w-full" />;
  const totals = bands.data.reduce(
    (sum, group) => ({
      below: sum.below + group.below,
      in_band: sum.in_band + group.in_band,
      above: sum.above + group.above,
    }),
    { below: 0, in_band: 0, above: 0 },
  );
  const banded = totals.below + totals.in_band + totals.above || 1;
  const width = (count: number) => `${(count / banded) * 100}%`;
  return (
    <div
      role="img"
      aria-label={`${totals.below} below band, ${totals.in_band} in band, ${totals.above} above band`}
      className="flex h-1.5 overflow-hidden rounded-full bg-muted"
    >
      <div className="bg-amber" style={{ width: width(totals.below) }} />
      <div className="bg-sage" style={{ width: width(totals.in_band) }} />
      <div className="bg-violet" style={{ width: width(totals.above) }} />
    </div>
  );
}

const ATTENTION: {
  type: ExceptionType;
  title: string;
  hint: string;
  tone: string;
  highlight?: boolean;
}[] = [
  {
    type: "below",
    title: "Paid below band",
    hint: "Base salary, at full-time equivalent, under the band minimum",
    tone: "text-amber-text",
    highlight: true,
  },
  {
    type: "pending",
    title: "Changes taking effect soon",
    hint: "Scheduled raises and promotions in the next 60 days",
    tone: "text-primary",
  },
  {
    type: "above",
    title: "Paid above band",
    hint: "Worth a look, not necessarily a problem",
    tone: "text-violet-text",
  },
  {
    type: "missing",
    title: "Missing a salary package",
    hint: "Excluded from averages until added",
    tone: "text-rose-text",
  },
];

function NeedsAttention() {
  const exceptions = useExceptions("below", 1, 1);
  return (
    <Panel title="Needs your attention" id="attention" aside={<Link href="/exceptions">View all</Link>}>
      {exceptions.isError ? (
        <ErrorState error={exceptions.error} onRetry={() => exceptions.refetch()} />
      ) : !exceptions.data ? (
        <LoadingRows rows={4} />
      ) : exceptions.data.counts.total === 0 ? (
        <EmptyState title="Nothing needs your attention">
          Everyone is paid within band and every change is recorded.
        </EmptyState>
      ) : (
        ATTENTION.map((item) => (
          <AttentionRow key={item.type} item={item} counts={exceptions.data.counts} />
        ))
      )}
    </Panel>
  );
}

function AttentionRow({
  item,
  counts,
}: {
  item: (typeof ATTENTION)[number];
  counts: ExceptionCounts;
}) {
  return (
    <Link
      href={`/exceptions?type=${item.type}`}
      className={cn(
        "flex items-center gap-3.5 rounded-[10px] border p-3.5 text-foreground hover:text-foreground hover:shadow-sm",
        item.highlight && "border-amber-line bg-amber-surface",
      )}
    >
      <span className={cn("amount min-w-14 text-[22px]", item.tone)}>
        {counts[item.type].toLocaleString("en-US")}
      </span>
      <span className="flex flex-1 flex-col gap-0.5">
        <span className="text-sm font-semibold">{item.title}</span>
        <span className="text-[13px] text-muted-foreground">{item.hint}</span>
      </span>
      <span aria-hidden="true" className="text-muted-foreground">
        →
      </span>
    </Link>
  );
}

function PayByCountry() {
  const countries = useBreakdown("country");
  const top = Math.max(...(countries.data ?? []).map((group) => group.median.amount_minor), 1);
  return (
    <Panel title="Median total pay by country" id="by-country" aside={<Link href="/insights">Open insights</Link>}>
      {countries.isError ? (
        <ErrorState error={countries.error} onRetry={() => countries.refetch()} />
      ) : !countries.data ? (
        <LoadingRows rows={8} className="gap-3" />
      ) : countries.data.length === 0 ? (
        <EmptyState title="No pay recorded yet" />
      ) : (
        <ul className="flex flex-col gap-3">
          {countries.data.map((group) => (
            <li
              key={group.key}
              className="grid grid-cols-[120px_minmax(0,1fr)_84px] items-center gap-3 text-[13px]"
            >
              <span>{group.label}</span>
              <span aria-hidden="true" className="h-2.5 rounded-full bg-muted">
                <span
                  className="block h-2.5 rounded-full bg-primary"
                  style={{ width: `${(group.median.amount_minor / top) * 100}%` }}
                />
              </span>
              <span className="amount text-right">{formatMoney(group.median)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted-foreground">
        Converted at fixed reference rates for comparison. Local-currency figures on each profile.
      </p>
    </Panel>
  );
}

function RecentChanges() {
  const changes = useRecentChanges(5);
  const countries = useCountries();
  const countryName = (code: string) =>
    countries.data?.find((country) => country.code === code)?.name ?? code;
  return (
    <Panel title="Recent pay changes" id="recent" aside="Latest recorded">
      {changes.isError ? (
        <ErrorState error={changes.error} onRetry={() => changes.refetch()} />
      ) : !changes.data ? (
        <LoadingRows rows={3} />
      ) : changes.data.length === 0 ? (
        <EmptyState title="No pay changes recorded yet" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="py-2 font-medium">Employee</th>
                <th className="py-2 font-medium">Reason</th>
                <th className="py-2 font-medium">Effective</th>
                <th className="py-2 text-right font-medium">Change</th>
              </tr>
            </thead>
            <tbody>
              {changes.data.map((change) => (
                <tr key={`${change.employee_id}-${change.effective_from}`} className="border-t border-muted">
                  <td className="py-3">
                    <Link href={`/employees/${change.employee_id}`} className="font-medium text-foreground">
                      {change.name}
                    </Link>{" "}
                    <span className="text-muted-foreground">
                      · {change.role.title} L{change.role.level} · {countryName(change.country_code)}
                    </span>
                  </td>
                  <td className="py-3">{REASON_LABELS[change.reason]}</td>
                  <td className="py-3">
                    {change.is_pending ? (
                      <span className="rounded-full bg-primary-tint px-2 py-0.5 text-xs text-primary-strong">
                        Pending · {formatDate(change.effective_from)}
                      </span>
                    ) : (
                      formatDate(change.effective_from)
                    )}
                  </td>
                  <td
                    className={cn(
                      "amount py-3 text-right",
                      Number(change.base_change_percent) > 0 ? "text-sage-text" : "text-muted-foreground",
                    )}
                  >
                    {formatChange(change.base_change_percent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function OverviewPage() {
  const me = useMe();
  const summary = useSummary();
  const data = summary.data;
  const firstName = me.data?.email.split(/[.@]/)[0] ?? "";

  return (
    <>
      <PageHeading
        title={`${greeting()}${firstName ? `, ${firstName[0].toUpperCase()}${firstName.slice(1)}` : ""}`}
        actions={
          <Button asChild className="h-10 px-4 font-semibold">
            <Link href="/employees/new" className="text-primary-foreground hover:text-primary-foreground">
              + Add employee
            </Link>
          </Button>
        }
      >
        Here&apos;s how ACME pays its people today, and what needs your attention.
      </PageHeading>

      {summary.isError ? <ErrorState error={summary.error} onRetry={() => summary.refetch()} /> : null}

      <section aria-label="Key figures" className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        <KpiCard label="Active headcount" value={data?.headcount.toLocaleString("en-US")}>
          {data ? (
            <span className="text-xs text-muted-foreground">
              +{data.joiners_this_quarter} joiners, −{data.leavers_this_quarter} leavers this quarter
            </span>
          ) : null}
        </KpiCard>
        <KpiCard
          label="Total annual pay (target)"
          value={data ? formatCompactUsd(data.total_pay_usd.amount_minor) : undefined}
        >
          <span className="text-xs text-muted-foreground">Base + allowances + target variable</span>
        </KpiCard>
        <KpiCard
          label="Median total pay"
          value={data ? (data.median_pay_usd ? formatMoney(data.median_pay_usd) : "—") : undefined}
        >
          <span className="text-xs text-muted-foreground">Across all countries, in USD</span>
        </KpiCard>
        <KpiCard label="Paid within band" value={data ? formatPercent(data.paid_within_band_percent) : undefined}>
          <BandMix />
        </KpiCard>
      </section>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(380px,1fr))] gap-4">
        <NeedsAttention />
        <PayByCountry />
      </div>

      <RecentChanges />
    </>
  );
}
