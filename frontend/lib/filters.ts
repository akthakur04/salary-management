/**
 * Directory filters live in the URL, so a view can be bookmarked and shared.
 * Unknown values are dropped rather than sent to the API.
 */

export const SORTS = [
  "name",
  "employee_code",
  "base",
  "total_pay_usd",
  "compa_ratio",
  "last_change",
] as const;
export const BAND_VALUES = ["below", "in_band", "above", "no_band"] as const;
export const TYPE_VALUES = ["full_time", "part_time", "contractor"] as const;
export const STATUS_VALUES = ["active", "on_leave", "terminated"] as const;
export const PAGE_SIZE = 25;

export type Sort = (typeof SORTS)[number];

export type Filters = {
  q: string;
  country: string;
  department: string;
  role: string;
  level: string;
  type: string;
  band: string;
  status: string;
  sort: Sort;
  order: "asc" | "desc";
  page: number;
};

export const DEFAULT_FILTERS: Filters = {
  q: "",
  country: "",
  department: "",
  role: "",
  level: "",
  type: "",
  band: "",
  status: "",
  sort: "name",
  order: "asc",
  page: 1,
};

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | "" {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

function digits(value: string | null): string {
  return value !== null && /^\d+$/.test(value) ? value : "";
}

export function filtersFromParams(params: URLSearchParams): Filters {
  const page = Number(params.get("page"));
  const sort = oneOf(params.get("sort"), SORTS);
  return {
    q: (params.get("q") ?? "").slice(0, 100),
    country: /^[A-Z]{2}$/.test(params.get("country") ?? "") ? (params.get("country") as string) : "",
    department: digits(params.get("department")),
    role: digits(params.get("role")),
    level: oneOf(params.get("level"), ["1", "2", "3", "4", "5"]),
    type: oneOf(params.get("type"), TYPE_VALUES),
    band: oneOf(params.get("band"), BAND_VALUES),
    status: oneOf(params.get("status"), STATUS_VALUES),
    sort: sort || DEFAULT_FILTERS.sort,
    order: params.get("order") === "desc" ? "desc" : "asc",
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

export function filtersToParams(filters: Filters): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of Object.keys(DEFAULT_FILTERS) as (keyof Filters)[]) {
    const value = filters[key];
    if (value !== DEFAULT_FILTERS[key] && value !== "") params.set(key, String(value));
  }
  return params;
}

/** The API's query parameters for the directory list (and its CSV export). */
export function toApiParams(filters: Filters, pageSize = PAGE_SIZE): URLSearchParams {
  const params = new URLSearchParams();
  const pairs: [string, string][] = [
    ["q", filters.q],
    ["country", filters.country],
    ["department", filters.department],
    ["role", filters.role],
    ["level", filters.level],
    ["band_position", filters.band],
    ["employment_type", filters.type],
    ["status", filters.status],
  ];
  for (const [name, value] of pairs) if (value) params.set(name, value);
  params.set("sort", filters.sort);
  params.set("order", filters.order);
  params.set("page", String(filters.page));
  params.set("page_size", String(pageSize));
  return params;
}
