import { cn } from "@/lib/utils";
import type { BandComparison, BandPosition } from "@/lib/types";

/**
 * Band position as colour + icon + text, never colour alone.
 * Below band is amber (something to review), never red; above is informational.
 */
const STYLES: Record<BandPosition, { icon: string; label: string; className: string }> = {
  in_band: { icon: "●", label: "In band", className: "bg-sage-tint text-sage-text" },
  below: { icon: "▼", label: "Below band", className: "bg-amber-tint text-amber-text" },
  above: { icon: "▲", label: "Above band", className: "bg-violet-tint text-violet-text" },
  no_band: { icon: "○", label: "No band", className: "bg-muted text-muted-foreground" },
};

export function bandLabel(position: BandPosition): string {
  return STYLES[position].label;
}

export function BandStatus({
  band,
  partTime = false,
  className,
}: {
  band: BandComparison | null;
  partTime?: boolean;
  className?: string;
}) {
  if (band === null) {
    return (
      <span className={cn("text-xs text-muted-foreground", className)}>No package</span>
    );
  }
  const style = STYLES[band.position];
  const detail = band.compa_ratio ? ` · ${band.compa_ratio}${partTime ? " FTE" : ""}` : "";
  return (
    <span
      data-status={band.position}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        style.className,
        className,
      )}
    >
      <span aria-hidden="true">{style.icon}</span>
      <span>{`${style.label}${detail}`}</span>
    </span>
  );
}
