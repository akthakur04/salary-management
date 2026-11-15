"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

const ANY = "__any";

/** A single-select filter chip: dashed when unset, tinted with its value when set. */
export function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  const chosen = options.find((option) => option.value === value);
  return (
    <Select value={value || ANY} onValueChange={(next) => onChange(next === ANY ? "" : next)}>
      <SelectTrigger
        aria-label={label}
        className={cn(
          "h-9 rounded-lg text-[13px]",
          chosen
            ? "border-[#C9CDEB] bg-primary-tint text-primary-strong"
            : "border-dashed border-input bg-card text-subtle-foreground",
        )}
      >
        <SelectValue>{chosen ? `${label}: ${chosen.label}` : label}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ANY}>Any {label.toLowerCase()}</SelectItem>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
