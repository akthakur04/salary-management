import { AlertCircleIcon, InboxIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Every data view has a loading, an empty and an error state (PRODUCT_DESIGN §2: reassurance). */

export function LoadingRows({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-3", className)} aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed px-6 py-10 text-center">
      <InboxIcon aria-hidden="true" className="size-5 text-muted-foreground" />
      <p className="text-sm font-semibold">{title}</p>
      {children ? <p className="max-w-md text-sm text-muted-foreground">{children}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError ? error.message : "We couldn't load this. Check your connection.";
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-xl bg-rose-tint px-4 py-3 text-sm text-rose-text"
    >
      <AlertCircleIcon aria-hidden="true" className="size-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
