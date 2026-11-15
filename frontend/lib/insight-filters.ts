/**
 * Insights filters live in the URL, like the directory's, so a drill-down such as
 * "India, engineering, in rupees" can be bookmarked and shared.
 */
import { DEFAULT_FILTERS, TYPE_VALUES, filtersToParams } from "./filters";

export const INSIGHT_GROUPS = [
  { key: "country", label: "Country" },
  { key: "department", label: "Department" },
  { key: "level", label: "Level" },
] as const;

export type GroupKey = (typeof INSIGHT_GROUPS)[number]["key"];
export type InsightCurrency = "local" | "usd";

export type InsightFilters = {
  country: string;
  department: string;
  level: string;
  type: string;
  group: GroupKey | "";
  /** Only applies when one country is selected; USD otherwise. */
  currency: InsightCurrency;
};

export const DEFAULT_INSIGHT_FILTERS: InsightFilters = {
  country: "",
  department: "",
  level: "",
  type: "",
  group: "",
  currency: "local",
};

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | "" {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

export function insightFiltersFromParams(params: URLSearchParams): InsightFilters {
  const country = params.get("country") ?? "";
  const department = params.get("department") ?? "";
  return {
    country: /^[A-Z]{2}$/.test(country) ? country : "",
    department: /^\d+$/.test(department) ? department : "",
    level: oneOf(params.get("level"), ["1", "2", "3", "4", "5"]),
    type: oneOf(params.get("type"), TYPE_VALUES),
    group: oneOf(
      params.get("group"),
      INSIGHT_GROUPS.map((g) => g.key),
    ),
    currency: params.get("currency") === "usd" ? "usd" : "local",
  };
}

export function insightFiltersToParams(filters: InsightFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of Object.keys(DEFAULT_INSIGHT_FILTERS) as (keyof InsightFilters)[]) {
    const value = filters[key];
    if (value && value !== DEFAULT_INSIGHT_FILTERS[key]) params.set(key, value);
  }
  return params;
}

/** Groupings still worth comparing: a dimension narrowed to one value has nothing to compare. */
export function groupOptions(filters: InsightFilters) {
  return INSIGHT_GROUPS.filter((group) => !filters[group.key]);
}

export function activeGroup(filters: InsightFilters): GroupKey | null {
  const options = groupOptions(filters);
  return options.find((option) => option.key === filters.group)?.key ?? options[0]?.key ?? null;
}

export function showsLocalCurrency(filters: InsightFilters): boolean {
  return Boolean(filters.country) && filters.currency === "local";
}

/** The API's query parameters for every insights panel. */
export function insightApiParams(filters: InsightFilters): URLSearchParams {
  const params = new URLSearchParams();
  const pairs: [string, string][] = [
    ["country", filters.country],
    ["department", filters.department],
    ["level", filters.level],
    ["employment_type", filters.type],
  ];
  for (const [name, value] of pairs) if (value) params.set(name, value);
  params.set("currency", showsLocalCurrency(filters) ? "local" : "usd");
  return params;
}

/** The employee directory, narrowed to the same people. */
export function directoryHref(filters: InsightFilters): string {
  const params = filtersToParams({
    ...DEFAULT_FILTERS,
    country: filters.country,
    department: filters.department,
    level: filters.level,
    type: filters.type,
  }).toString();
  return params ? `/employees?${params}` : "/employees";
}
