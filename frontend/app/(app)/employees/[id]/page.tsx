"use client";

import Link from "next/link";
import { use } from "react";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { BandPanel } from "@/features/profile/band-panel";
import { EditDetailsDialog } from "@/features/profile/edit-details-dialog";
import { HistoryPanel } from "@/features/profile/history-panel";
import { PackagePanel } from "@/features/profile/package-panel";
import { ApiError } from "@/lib/api";
import { employmentLabel, formatDate, initials, STATUS_LABELS } from "@/lib/format";
import { useEmployee, useRoles } from "@/lib/queries";
import type { EmployeeProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_CHIP = {
  active: "bg-sage-tint text-sage-text",
  on_leave: "bg-amber-tint text-amber-text",
  terminated: "bg-muted text-muted-foreground",
} as const;

function Header({ profile }: { profile: EmployeeProfile }) {
  const role = profile.role;
  const leaving =
    profile.termination_date && profile.status !== "terminated"
      ? ` · Last day ${formatDate(profile.termination_date)}`
      : profile.termination_date
        ? ` · Left ${formatDate(profile.termination_date)}`
        : "";
  return (
    <section
      aria-label="Employee"
      className="flex flex-wrap items-center justify-between gap-5 rounded-xl border bg-card p-6"
    >
      <div className="flex items-center gap-4">
        <span
          aria-hidden="true"
          className="flex size-14 items-center justify-center rounded-full bg-primary-tint text-lg font-semibold text-primary-strong"
        >
          {initials(profile.name)}
        </span>
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight">{profile.name}</h1>
            <span className="amount text-xs text-muted-foreground">{profile.employee_code}</span>
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", STATUS_CHIP[profile.status])}>
              {STATUS_LABELS[profile.status]}
            </span>
          </div>
          <span className="text-sm text-subtle-foreground">
            {role
              ? `${role.title} · L${role.level} · ${role.department}${profile.country ? ` · ${profile.country.name}` : ""}`
              : "No role recorded yet"}
          </span>
          <span className="text-[13px] text-muted-foreground">
            {employmentLabel(profile.employment_type, profile.fte)} · Joined {formatDate(profile.hire_date)}
            {profile.currency ? ` · Paid in ${profile.currency}` : ""}
            {leaving}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <EditDetailsDialog key={`${profile.name}-${profile.status}-${profile.termination_date}`} profile={profile} />
        {profile.status !== "terminated" ? (
          <Button asChild className="h-10 px-4 font-semibold">
            <Link
              href={`/employees/${profile.id}/revise`}
              className="text-primary-foreground hover:text-primary-foreground"
            >
              Revise compensation
            </Link>
          </Button>
        ) : null}
      </div>
    </section>
  );
}

function PendingNotice({ profile }: { profile: EmployeeProfile }) {
  if (profile.pending_changes.length === 0) return null;
  const next = profile.pending_changes[0];
  return (
    <p className="rounded-xl border border-[#C9CDEB] bg-primary-tint px-4 py-3 text-sm text-primary-strong">
      A change is scheduled for <b>{formatDate(next.effective_from)}</b>. The current package stays in
      force until then.
    </p>
  );
}

export default function EmployeePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const employeeId = Number(id);
  const employee = useEmployee(employeeId);
  const roles = useRoles();

  if (employee.isError) {
    const notFound = employee.error instanceof ApiError && employee.error.status === 404;
    return notFound ? (
      <EmptyState title="We couldn't find that employee" action={<Link href="/employees">Back to Employees</Link>}>
        They may have been removed from this view, or the link is wrong.
      </EmptyState>
    ) : (
      <ErrorState error={employee.error} onRetry={() => employee.refetch()} />
    );
  }
  if (!employee.data) return <LoadingRows rows={8} />;

  const profile = employee.data;
  const defaults = roles.data?.find((role) => role.id === profile.role?.id)?.defaults ?? [];

  return (
    <>
      <nav aria-label="Breadcrumb" className="-mb-2 text-[13px] text-muted-foreground">
        <Link href="/employees">Employees</Link> / <span>{profile.name}</span>
      </nav>
      <Header profile={profile} />
      {profile.package ? <PendingNotice profile={profile} /> : null}
      {profile.package ? (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(400px,1fr))] gap-5">
          <PackagePanel profile={profile} pkg={profile.package} defaults={defaults} />
          <BandPanel profile={profile} />
        </div>
      ) : (
        <EmptyState
          title="No salary package in force"
          action={
            profile.status !== "terminated" && profile.pending_changes.length === 0 ? (
              <Button asChild size="sm">
                <Link href={`/employees/${profile.id}/revise`} className="text-primary-foreground">
                  Record a package
                </Link>
              </Button>
            ) : null
          }
        >
          {profile.pending_changes.length
            ? `Their first package starts on ${formatDate(profile.pending_changes[0].effective_from)}. It's listed in the history below.`
            : "This person is left out of pay averages until a package is recorded."}
        </EmptyState>
      )}
      <HistoryPanel employeeId={profile.id} />
    </>
  );
}
