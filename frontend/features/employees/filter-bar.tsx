"use client";

import { SearchIcon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { bandLabel } from "@/components/band-status";
import { BAND_VALUES, type Filters } from "@/lib/filters";
import { EMPLOYMENT_TYPE_LABELS, STATUS_LABELS } from "@/lib/format";
import { useCountries, useDepartments } from "@/lib/queries";
import type { BandPosition, EmploymentStatus, EmploymentType } from "@/lib/types";
import { useDebounced } from "@/lib/use-debounced";
import { cn } from "@/lib/utils";

type FilterKey = "country" | "department" | "level" | "type" | "band" | "status";

const ANY = "__any";

function FilterSelect({
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

export function FilterBar({
  filters,
  onChange,
  onClear,
}: {
  filters: Filters;
  onChange: (changes: Partial<Filters>) => void;
  onClear: () => void;
}) {
  const countries = useCountries();
  const departments = useDepartments();
  const [query, setQuery] = useState(filters.q);
  const debounced = useDebounced(query.trim(), 300);

  useEffect(() => {
    if (debounced !== filters.q) onChange({ q: debounced });
    // Only the debounced search text should trigger this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  const set = (key: FilterKey) => (value: string) => onChange({ [key]: value });
  const anyFilter =
    filters.q ||
    filters.country ||
    filters.department ||
    filters.level ||
    filters.type ||
    filters.band ||
    filters.status;

  return (
    <section
      aria-label="Filters"
      className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-3"
    >
      <label className="flex h-9 flex-[1_1_260px] items-center gap-2 rounded-lg border px-2.5 text-muted-foreground focus-within:border-primary">
        <SearchIcon aria-hidden="true" className="size-4" />
        <input
          aria-label="Search by name or employee ID"
          placeholder="Name or employee ID"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none"
        />
        {query ? (
          <button type="button" aria-label="Clear search" onClick={() => setQuery("")}>
            <XIcon className="size-4" />
          </button>
        ) : null}
      </label>
      <FilterSelect
        label="Country"
        value={filters.country}
        onChange={set("country")}
        options={(countries.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
      />
      <FilterSelect
        label="Department"
        value={filters.department}
        onChange={set("department")}
        options={(departments.data ?? []).map((d) => ({ value: String(d.id), label: d.name }))}
      />
      <FilterSelect
        label="Level"
        value={filters.level}
        onChange={set("level")}
        options={["1", "2", "3", "4", "5"].map((level) => ({ value: level, label: `L${level}` }))}
      />
      <FilterSelect
        label="Employment type"
        value={filters.type}
        onChange={set("type")}
        options={(Object.keys(EMPLOYMENT_TYPE_LABELS) as EmploymentType[]).map((type) => ({
          value: type,
          label: EMPLOYMENT_TYPE_LABELS[type],
        }))}
      />
      <FilterSelect
        label="Band position"
        value={filters.band}
        onChange={set("band")}
        options={BAND_VALUES.map((band) => ({ value: band, label: bandLabel(band as BandPosition) }))}
      />
      <FilterSelect
        label="Status"
        value={filters.status}
        onChange={set("status")}
        options={(Object.keys(STATUS_LABELS) as EmploymentStatus[]).map((status) => ({
          value: status,
          label: STATUS_LABELS[status],
        }))}
      />
      {anyFilter ? (
        <button
          type="button"
          onClick={() => {
            setQuery("");
            onClear();
          }}
          className="h-9 px-2 text-[13px] text-primary underline"
        >
          Clear
        </button>
      ) : null}
    </section>
  );
}
