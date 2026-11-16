import { formatMoney } from "@/lib/format";
import type { BandPosition, BandRange, Money } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Where a (full-time-equivalent) base sits in its band: the track runs from
 * minimum to maximum, with the midpoint marked. Pay outside the band is pinned
 * to the edge in amber (below) or slate violet (above).
 */
export function BandGauge({
  band,
  value,
  position,
  className,
}: {
  band: BandRange;
  value: Money;
  position: BandPosition;
  className?: string;
}) {
  const min = band.minimum.amount_minor;
  const max = band.maximum.amount_minor;
  const span = Math.max(max - min, 1);
  const at = Math.min(100, Math.max(0, ((value.amount_minor - min) / span) * 100));
  const mid = ((band.midpoint.amount_minor - min) / span) * 100;
  const marker = position === "below" ? "bg-amber" : position === "above" ? "bg-violet" : "bg-foreground";

  return (
    <div
      role="img"
      aria-label={`${formatMoney(value)} against a band of ${formatMoney(band.minimum)} to ${formatMoney(band.maximum)}, midpoint ${formatMoney(band.midpoint)}`}
      className={cn("flex flex-col gap-2", className)}
    >
      <div className="relative h-7">
        <div className="absolute inset-x-0 top-2.5 h-2 rounded-full bg-sage-tint" />
        <div className="absolute top-1 h-5 w-0.5 bg-sage" style={{ left: `${mid}%` }} />
        <div
          className={cn("absolute top-0 -ml-0.5 h-7 w-1 rounded-sm transition-[left]", marker)}
          style={{ left: `${at}%` }}
        />
      </div>
      <div className="amount flex justify-between text-xs text-muted-foreground">
        <span>Min {formatMoney(band.minimum)}</span>
        <span>Mid {formatMoney(band.midpoint)}</span>
        <span>Max {formatMoney(band.maximum)}</span>
      </div>
    </div>
  );
}
