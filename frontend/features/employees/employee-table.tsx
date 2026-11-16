"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import Link from "next/link";

import { BandStatus } from "@/components/band-status";
import { type Filters, type Sort } from "@/lib/filters";
import { employmentLabel, formatDate, formatMoney } from "@/lib/format";
import type { EmployeeSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

type Column = ColumnDef<EmployeeSummary> & { meta?: { sort?: Sort; numeric?: boolean } };

const COLUMNS: Column[] = [
  {
    id: "employee",
    header: "Employee",
    meta: { sort: "name" },
    cell: ({ row }) => (
      <Link href={`/employees/${row.original.id}`} className="flex flex-col">
        <span className="font-semibold text-foreground">{row.original.name}</span>
        <span className="amount text-xs text-muted-foreground">{row.original.employee_code}</span>
      </Link>
    ),
  },
  {
    id: "role",
    header: "Role",
    cell: ({ row }) =>
      row.original.role ? `${row.original.role.title} · L${row.original.role.level}` : "—",
  },
  {
    id: "type",
    header: "Type",
    cell: ({ row }) => employmentLabel(row.original.employment_type, row.original.fte),
  },
  {
    id: "base",
    header: "Base salary",
    meta: { sort: "base", numeric: true },
    cell: ({ row }) => (row.original.base_salary ? formatMoney(row.original.base_salary) : "—"),
  },
  {
    id: "total",
    header: "Total pay (USD)",
    meta: { sort: "total_pay_usd", numeric: true },
    cell: ({ row }) => (row.original.total_pay_usd ? formatMoney(row.original.total_pay_usd) : "—"),
  },
  {
    id: "band",
    header: "Band position",
    meta: { sort: "compa_ratio" },
    cell: ({ row }) => (
      <BandStatus band={row.original.band} partTime={row.original.employment_type === "part_time"} />
    ),
  },
  {
    id: "last_change",
    header: "Last change",
    meta: { sort: "last_change" },
    cell: ({ row }) =>
      row.original.last_change ? (
        <span className="text-muted-foreground">{formatDate(row.original.last_change)}</span>
      ) : (
        "—"
      ),
  },
];

/** Server-side table: the API pages and sorts; the table only renders the current page. */
export function EmployeeTable({
  rows,
  filters,
  onSort,
  loading,
}: {
  rows: EmployeeSummary[];
  filters: Filters;
  onSort: (sort: Sort) => void;
  loading: boolean;
}) {
  const table = useReactTable({
    data: rows,
    columns: COLUMNS,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
  });

  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full min-w-[980px] text-sm", loading && "opacity-60")} aria-busy={loading}>
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id} className="bg-[#FBFAF8] text-left text-xs text-muted-foreground">
              {group.headers.map((header) => {
                const meta = (header.column.columnDef as Column).meta;
                const sorted = meta?.sort === filters.sort;
                const label = flexRender(header.column.columnDef.header, header.getContext());
                return (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={sorted ? (filters.order === "asc" ? "ascending" : "descending") : undefined}
                    className={cn("px-4 py-2.5 font-medium", meta?.numeric && "text-right")}
                  >
                    {meta?.sort ? (
                      <button
                        type="button"
                        onClick={() => onSort(meta.sort as Sort)}
                        className={cn("hover:text-foreground", sorted && "text-foreground")}
                      >
                        {label}
                        {sorted ? (filters.order === "asc" ? " ↑" : " ↓") : null}
                      </button>
                    ) : (
                      label
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-t border-muted hover:bg-[#FAFAFE]">
              {row.getVisibleCells().map((cell) => {
                const meta = (cell.column.columnDef as Column).meta;
                return (
                  <td
                    key={cell.id}
                    className={cn("px-4 py-3", meta?.numeric && "amount text-right")}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
