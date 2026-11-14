"use client";

import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PageHeading, Panel } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { BandChart, MixChart } from "@/features/insights/charts";
import { exportUrl } from "@/lib/api";
import { formatMoney, formatPercent } from "@/lib/format";
import { useBandDistribution, useBreakdown } from "@/lib/queries";
import type { PayGroup } from "@/lib/types";
import { cn } from "@/lib/utils";

const GROUPS = [
  { key: "country", label: "Country" },
  { key: "department", label: "Department" },
  { key: "level", label: "Level" },
] as const;

type GroupKey = (typeof GROUPS)[number]["key"];

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

function InsightsView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const group: GroupKey = GROUPS.some((g) => g.key === params.get("group")) ? (params.get("group") as GroupKey) : "country";
  const groupLabel = GROUPS.find((g) => g.key === group)?.label ?? "Country";
  const breakdown = useBreakdown(group);
  const mix = useBreakdown("department");
  const bands = useBandDistribution("department");

  return (
    <>
      <PageHeading
        title="How ACME pays people"
        actions={
          <Button variant="outline" asChild className="h-10 bg-card px-3.5">
            <a href={exportUrl(new URLSearchParams())} download className="text-foreground hover:text-foreground">
              <DownloadIcon aria-hidden="true" />
              Export CSV
            </a>
          </Button>
        }
      >
        Compare pay across countries, departments and levels. Active employees, total target pay in USD at reference
        rates.
      </PageHeading>

      <Panel
        title={`Total pay by ${groupLabel.toLowerCase()}`}
        id="by-group"
        aside={
          <div role="group" aria-label="Group by" className="flex gap-1 rounded-[10px] bg-muted p-1">
            {GROUPS.map((option) => (
              <button
                key={option.key}
                type="button"
                aria-pressed={option.key === group}
                onClick={() => router.replace(`${pathname}?group=${option.key}`, { scroll: false })}
                className={cn(
                  "h-9 rounded-lg px-3.5 text-[13px]",
                  option.key === group ? "bg-card font-semibold text-foreground shadow-sm" : "text-subtle-foreground hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      >
        {breakdown.isError ? (
          <ErrorState error={breakdown.error} onRetry={() => breakdown.refetch()} />
        ) : !breakdown.data ? (
          <LoadingRows rows={8} />
        ) : breakdown.data.length === 0 ? (
          <EmptyState title="No pay recorded yet" />
        ) : (
          <div className={cn(breakdown.isPlaceholderData && "opacity-60")}>
            <RangeTable groups={ordered(breakdown.data, group)} groupLabel={groupLabel} />
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(420px,1fr))] gap-4">
        <Panel title="Fixed vs. variable pay" id="mix" aside="Share of total target pay, by department">
          {mix.isError ? (
            <ErrorState error={mix.error} onRetry={() => mix.refetch()} />
          ) : !mix.data ? (
            <LoadingRows rows={6} />
          ) : mix.data.length === 0 ? (
            <EmptyState title="No pay recorded yet" />
          ) : (
            <MixChart groups={mix.data} />
          )}
        </Panel>
        <Panel title="Position against pay bands" id="bands" aside={<Link href="/exceptions">See exceptions</Link>}>
          {bands.isError ? (
            <ErrorState error={bands.error} onRetry={() => bands.refetch()} />
          ) : !bands.data ? (
            <LoadingRows rows={6} />
          ) : bands.data.length === 0 ? (
            <EmptyState title="No banded employees yet" />
          ) : (
            <>
              <BandChart groups={bands.data} />
              <p className="text-xs text-muted-foreground">
                In band overall:{" "}
                {formatPercent(
                  (() => {
                    const totals = bands.data.reduce((sum, g) => ({ in: sum.in + g.in_band, all: sum.all + g.banded }), { in: 0, all: 0 });
                    return totals.all ? ((totals.in * 100) / totals.all).toFixed(1) : null;
                  })(),
                )}
                . Contractors aren&apos;t banded and are left out.
              </p>
            </>
          )}
        </Panel>
      </div>
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
