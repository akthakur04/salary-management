"use client";

import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback } from "react";

import { PageHeading } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { EmployeeTable } from "@/features/employees/employee-table";
import { FilterBar } from "@/features/employees/filter-bar";
import { exportUrl } from "@/lib/api";
import {
  DEFAULT_FILTERS,
  filtersFromParams,
  filtersToParams,
  PAGE_SIZE,
  toApiParams,
  type Filters,
  type Sort,
} from "@/lib/filters";
import { useEmployees } from "@/lib/queries";

const SORT_LABELS: Record<Sort, string> = {
  name: "name",
  employee_code: "employee code",
  base: "base salary",
  total_pay_usd: "total pay (USD)",
  compa_ratio: "compa-ratio",
  last_change: "last change",
};

function Directory() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filters = filtersFromParams(params);
  const employees = useEmployees(filters);

  const update = useCallback(
    (changes: Partial<Filters>) => {
      // Any change other than paging starts again at page 1.
      const next = { ...filters, ...changes, page: changes.page ?? 1 };
      const query = filtersToParams(next).toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [filters, pathname, router],
  );

  function sortBy(sort: Sort) {
    const order = filters.sort === sort && filters.order === "asc" ? "desc" : "asc";
    update({ sort, order });
  }

  const data = employees.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const first = data && data.total ? (data.page - 1) * PAGE_SIZE + 1 : 0;
  const last = data ? Math.min(data.page * PAGE_SIZE, data.total) : 0;
  const exportParams = toApiParams(filters);
  exportParams.delete("page");
  exportParams.delete("page_size");

  return (
    <>
      <PageHeading
        title="Employees"
        actions={
          <>
            <Button variant="outline" asChild className="h-10 bg-card px-3.5">
              <a href={exportUrl(exportParams)} download className="text-foreground hover:text-foreground">
                <DownloadIcon aria-hidden="true" />
                Export CSV
              </a>
            </Button>
            <Button asChild className="h-10 px-4 font-semibold">
              <Link href="/employees/new" className="text-primary-foreground hover:text-primary-foreground">
                + Add employee
              </Link>
            </Button>
          </>
        }
      >
        Search, filter and sort everyone on record. Filters stay in the address, so you can share a view.
      </PageHeading>

      <FilterBar filters={filters} onChange={update} onClear={() => update(DEFAULT_FILTERS)} />

      <section aria-label="Results" className="overflow-hidden rounded-xl border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-muted px-4 py-3 text-[13px] text-muted-foreground">
          <span aria-live="polite">
            <span className="amount text-foreground">{data ? data.total.toLocaleString("en-US") : "…"}</span>{" "}
            {data?.total === 1 ? "employee matches" : "employees match"}
          </span>
          <span>
            Sorted by {SORT_LABELS[filters.sort]} · base in local currency
          </span>
        </div>

        {employees.isError ? (
          <div className="p-4">
            <ErrorState error={employees.error} onRetry={() => employees.refetch()} />
          </div>
        ) : !data ? (
          <LoadingRows rows={10} className="p-4" />
        ) : data.items.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No one matches these filters"
              action={
                <Button variant="outline" size="sm" onClick={() => update(DEFAULT_FILTERS)}>
                  Clear filters
                </Button>
              }
            >
              Try a broader search, or clear a filter.
            </EmptyState>
          </div>
        ) : (
          <EmployeeTable
            rows={data.items}
            filters={filters}
            onSort={sortBy}
            loading={employees.isPlaceholderData}
          />
        )}

        {data && data.total > 0 ? (
          <nav
            aria-label="Pages"
            className="flex flex-wrap items-center justify-between gap-3 border-t border-muted px-4 py-3 text-[13px] text-muted-foreground"
          >
            <span>
              Showing <span className="amount text-foreground">{first.toLocaleString("en-US")}–{last.toLocaleString("en-US")}</span> of{" "}
              <span className="amount text-foreground">{data.total.toLocaleString("en-US")}</span>
            </span>
            <span className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={data.page <= 1}
                onClick={() => update({ page: data.page - 1 })}
              >
                Previous
              </Button>
              <span>
                Page <span className="amount text-foreground">{data.page}</span> of {pages.toLocaleString("en-US")}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={data.page >= pages}
                onClick={() => update({ page: data.page + 1 })}
              >
                Next
              </Button>
            </span>
          </nav>
        ) : null}
      </section>
    </>
  );
}

export default function EmployeesPage() {
  return (
    <Suspense fallback={<LoadingRows rows={10} />}>
      <Directory />
    </Suspense>
  );
}
