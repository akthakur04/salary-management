"use client";

import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PageHeading } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { exportUrl } from "@/lib/api";
import { formatChange, formatDate, formatMoney, REASON_LABELS } from "@/lib/format";
import { useExceptions } from "@/lib/queries";
import type { ExceptionItem, ExceptionType } from "@/lib/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

type Column = { label: string; numeric?: boolean; render: (item: ExceptionItem) => React.ReactNode };

const money = (value: ExceptionItem["base_salary"]) => (value ? formatMoney(value) : "—");

const TABS: Record<
  ExceptionType,
  {
    label: string;
    title: string;
    hint: string;
    chip: string;
    columns: Column[];
    action: string;
    band?: "below" | "above";
  }
> = {
  below: {
    label: "Below band",
    title: "Paid below band minimum",
    hint: "Base salary (at FTE) is under the minimum for the role, level and country.",
    chip: "bg-amber-tint text-amber-text",
    action: "Review",
    band: "below",
    columns: [
      { label: "Base salary", numeric: true, render: (i) => money(i.base_salary) },
      { label: "Band minimum", numeric: true, render: (i) => money(i.band_minimum) },
      {
        label: "Gap",
        numeric: true,
        render: (i) => (
          <span className="rounded-full bg-amber-tint px-2.5 py-0.5 text-xs text-amber-text">
            {formatChange(i.gap_percent)} · {money(i.gap)}
          </span>
        ),
      },
    ],
  },
  above: {
    label: "Above band",
    title: "Paid above band maximum",
    hint: "Often deliberate (retention, scarce skills). Worth confirming, not necessarily fixing.",
    chip: "bg-violet-tint text-violet-text",
    action: "Review",
    band: "above",
    columns: [
      { label: "Base salary", numeric: true, render: (i) => money(i.base_salary) },
      { label: "Band maximum", numeric: true, render: (i) => money(i.band_maximum) },
      {
        label: "Over by",
        numeric: true,
        render: (i) => (
          <span className="rounded-full bg-violet-tint px-2.5 py-0.5 text-xs text-violet-text">
            {formatChange(i.gap_percent)}
          </span>
        ),
      },
    ],
  },
  pending: {
    label: "Pending changes",
    title: "Changes taking effect in the next 60 days",
    hint: "Already saved and future-dated. The current package stays in force until the date.",
    chip: "bg-primary-tint text-primary-strong",
    action: "Open",
    columns: [
      { label: "Base today", numeric: true, render: (i) => money(i.base_salary) },
      { label: "New base", numeric: true, render: (i) => money(i.new_base_salary) },
      {
        label: "Effective",
        render: (i) =>
          i.effective_from ? (
            <span className="rounded-full bg-primary-tint px-2.5 py-0.5 text-xs text-primary-strong">
              {i.reason ? `${REASON_LABELS[i.reason]} · ` : ""}
              {formatDate(i.effective_from)}
            </span>
          ) : (
            "—"
          ),
      },
    ],
  },
  missing: {
    label: "Missing package",
    title: "Missing a salary package",
    hint: "No compensation is recorded, so they're left out of pay averages until one is added.",
    chip: "bg-rose-tint text-rose-text",
    action: "Add package",
    columns: [],
  },
};

const ORDER: ExceptionType[] = ["below", "above", "pending", "missing"];

function isExceptionType(value: string | null): value is ExceptionType {
  return value !== null && (ORDER as string[]).includes(value);
}

function ExceptionsView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const type: ExceptionType = isExceptionType(params.get("type")) ? (params.get("type") as ExceptionType) : "below";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const exceptions = useExceptions(type, page, PAGE_SIZE);
  const tab = TABS[type];
  const data = exceptions.data;

  function go(next: { type?: ExceptionType; page?: number }) {
    const query = new URLSearchParams();
    query.set("type", next.type ?? type);
    if ((next.page ?? 1) > 1) query.set("page", String(next.page));
    router.replace(`${pathname}?${query}`, { scroll: false });
  }

  const exportParams = new URLSearchParams(tab.band ? { band_position: tab.band } : {});

  return (
    <>
      <PageHeading title="Exceptions">
        Your review list: pay that sits outside policy, data that&apos;s missing, and changes about to land.
      </PageHeading>

      <div role="tablist" aria-label="Exception types" className="flex flex-wrap gap-2">
        {ORDER.map((key) => {
          const selected = key === type;
          return (
            <button
              key={key}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls="exception-panel"
              onClick={() => go({ type: key })}
              className={cn(
                "flex h-10 items-center gap-2 rounded-[10px] border px-3.5 text-sm",
                selected ? "border-primary bg-card font-semibold text-foreground shadow-sm" : "bg-card text-subtle-foreground hover:text-foreground",
              )}
            >
              {TABS[key].label}
              <span className={cn("amount rounded-full px-2 py-0.5 text-xs", TABS[key].chip)}>
                {data ? data.counts[key].toLocaleString("en-US") : "…"}
              </span>
            </button>
          );
        })}
      </div>

      <section id="exception-panel" role="tabpanel" aria-labelledby="exception-title" className="overflow-hidden rounded-xl border bg-card">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-muted px-5 py-4">
          <div className="flex flex-col gap-1">
            <h2 id="exception-title" className="text-base font-semibold">
              {tab.title}
            </h2>
            <p className="text-[13px] text-muted-foreground">{tab.hint}</p>
          </div>
          {tab.band ? (
            <Button variant="outline" size="sm" asChild>
              <a href={exportUrl(exportParams)} download className="text-foreground hover:text-foreground">
                <DownloadIcon aria-hidden="true" />
                Export list
              </a>
            </Button>
          ) : null}
        </div>

        {exceptions.isError ? (
          <div className="p-4">
            <ErrorState error={exceptions.error} onRetry={() => exceptions.refetch()} />
          </div>
        ) : !data ? (
          <LoadingRows rows={8} className="p-4" />
        ) : data.items.length === 0 ? (
          <div className="p-4">
            <EmptyState title={`No one here right now`}>
              {type === "pending" ? "No changes take effect in the next 60 days." : "Nothing needs reviewing in this list."}
            </EmptyState>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className={cn("w-full min-w-[860px] text-sm", exceptions.isPlaceholderData && "opacity-60")}>
              <thead>
                <tr className="bg-[#FBFAF8] text-left text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-2.5 font-medium">Employee</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Role · Country</th>
                  {tab.columns.map((column) => (
                    <th key={column.label} scope="col" className={cn("px-4 py-2.5 font-medium", column.numeric && "text-right")}>
                      {column.label}
                    </th>
                  ))}
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">
                    <span className="sr-only">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.employee_id} className="border-t border-muted">
                    <td className="px-4 py-3">
                      <span className="flex flex-col">
                        <span className="font-semibold">{item.name}</span>
                        <span className="amount text-xs text-muted-foreground">{item.employee_code}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-subtle-foreground">
                      {item.role ? `${item.role.title} L${item.role.level}` : "No role"}
                      {item.country_code ? ` · ${item.country_code}` : ""}
                    </td>
                    {tab.columns.map((column) => (
                      <td key={column.label} className={cn("px-4 py-3", column.numeric && "amount text-right")}>
                        {column.render(item)}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={type === "missing" ? `/employees/${item.employee_id}/revise` : `/employees/${item.employee_id}`}
                        className="text-sm font-medium"
                      >
                        {tab.action}
                        <span className="sr-only"> {item.name}</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > 0 ? (
          <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-3 border-t border-muted px-4 py-3 text-[13px] text-muted-foreground">
            <span>
              Showing <span className="amount text-foreground">{data.items.length}</span> of{" "}
              <span className="amount text-foreground">{data.total.toLocaleString("en-US")}</span>
              {tab.band ? " · sorted by largest gap first" : ""}
            </span>
            <span className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => go({ page: page - 1 })}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page * PAGE_SIZE >= data.total} onClick={() => go({ page: page + 1 })}>
                Next
              </Button>
            </span>
          </nav>
        ) : null}
      </section>

      <p className="text-[13px] text-muted-foreground">
        Contractors aren&apos;t banded, so they never appear under band exceptions. Part-time employees are compared at
        full-time equivalent.
      </p>
    </>
  );
}

export default function ExceptionsPage() {
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <ExceptionsView />
    </Suspense>
  );
}
