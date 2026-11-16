import { Panel } from "@/components/page-heading";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { formatChange, formatDate, formatMoney, REASON_LABELS } from "@/lib/format";
import { useHistory } from "@/lib/queries";
import type { HistoryEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

function describe(entry: HistoryEntry, previous: HistoryEntry | undefined): { title: string; detail: string } {
  if (!previous) {
    const allowances = entry.components.filter((c) => c.type === "allowance").map((c) => c.label.toLowerCase());
    return {
      title: `${REASON_LABELS[entry.reason]} · ${entry.role.title} L${entry.role.level}`,
      detail: `Base ${formatMoney(entry.base_salary)}${allowances.length ? ` · ${allowances.join(" & ")}` : ""}`,
    };
  }
  const levelChange =
    previous.role.id !== entry.role.id
      ? previous.role.title === entry.role.title
        ? ` · L${previous.role.level} → L${entry.role.level}`
        : ` · ${previous.role.title} → ${entry.role.title}`
      : "";
  const moved = previous.country_code !== entry.country_code ? ` · ${previous.country_code} → ${entry.country_code}` : "";
  return {
    title: `${REASON_LABELS[entry.reason]}${levelChange}${moved}`,
    detail: `Base ${formatMoney(previous.base_salary)} → ${formatMoney(entry.base_salary)}`,
  };
}

const STATE_CHIPS: Partial<Record<HistoryEntry["state"], { label: string; className: string }>> = {
  current: { label: "Current", className: "bg-primary-tint text-primary-strong" },
  pending: { label: "Pending", className: "bg-primary-tint text-primary-strong" },
  superseded: { label: "Replaced by a correction", className: "bg-muted text-muted-foreground" },
};

export function HistoryPanel({ employeeId }: { employeeId: number }) {
  const history = useHistory(employeeId);
  const entries = history.data ?? [];
  // The API lists newest first; the previous version is the next one in the list.
  return (
    <Panel title="Compensation history" id="history">
      {history.isError ? (
        <ErrorState error={history.error} onRetry={() => history.refetch()} />
      ) : !history.data ? (
        <LoadingRows rows={4} />
      ) : entries.length === 0 ? (
        <EmptyState title="No compensation recorded yet" />
      ) : (
        <ol className="flex flex-col">
          {entries.map((entry, index) => {
            const { title, detail } = describe(entry, entries[index + 1]);
            const chip = STATE_CHIPS[entry.state];
            const change = Number(entry.base_change_percent);
            return (
              <li
                key={entry.version_id}
                className="grid grid-cols-[20px_120px_minmax(0,1fr)_auto] items-start gap-4 border-b border-muted py-3 last:border-0"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "mt-1.5 size-2.5 rounded-full",
                    entry.state === "current" ? "bg-primary" : "border-2 border-[#9BA1AC]",
                  )}
                />
                <span className="text-sm font-medium">{formatDate(entry.effective_from)}</span>
                <span className="flex flex-col gap-0.5">
                  <span className="text-sm">
                    {title}{" "}
                    {chip ? (
                      <span className={cn("rounded-full px-2 py-px text-[11px] font-medium", chip.className)}>
                        {chip.label}
                      </span>
                    ) : null}
                  </span>
                  <span className="text-[13px] text-muted-foreground">{detail}</span>
                  {entry.note ? <span className="text-[13px] text-subtle-foreground">“{entry.note}”</span> : null}
                </span>
                <span className={cn("amount text-sm", change > 0 ? "text-sage-text" : "text-muted-foreground")}>
                  {formatChange(entry.base_change_percent)}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}
