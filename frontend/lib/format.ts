import type { ChangeReason, EmploymentStatus, EmploymentType, Money } from "./types";

/**
 * Every amount is shown with its currency, in that currency's own grouping:
 * INR uses lakh grouping (₹24,00,000), others use thousands (€118,000).
 */
const SYMBOLS: Record<string, string> = {
  USD: "$",
  INR: "₹",
  EUR: "€",
  GBP: "£",
  SGD: "S$",
  BRL: "R$",
  CAD: "C$",
  AUD: "A$",
};

const MINUS = "−"; // U+2212, as typeset in the design

export function minorToMajor(amountMinor: number): number {
  return amountMinor / 100;
}

export function majorToMinor(amountMajor: number): number {
  return Math.round(amountMajor * 100);
}

export function groupNumber(value: number, currency: string, fractionDigits = 0): string {
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatMoney(money: Money, options: { cents?: boolean } = {}): string {
  const major = minorToMajor(money.amount_minor);
  const digits = options.cents ? 2 : 0;
  const grouped = groupNumber(Math.abs(major), money.currency, digits);
  const symbol = SYMBOLS[money.currency];
  const text = symbol ? `${symbol}${grouped}` : `${money.currency} ${grouped}`;
  return major < 0 ? `${MINUS}${text}` : text;
}

export function currencySymbol(currency: string): string {
  return SYMBOLS[currency] ?? currency;
}

export function formatCompactUsd(amountMinor: number): string {
  const formatted = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(minorToMajor(amountMinor));
  return `$${formatted}`;
}

/** A signed change such as "+12.0%" or "−1.2%". The API sends one-decimal strings. */
export function formatChange(percent: string | null): string {
  if (percent === null) return "—";
  const value = Number(percent);
  if (value > 0) return `+${percent}%`;
  if (value < 0) return `${MINUS}${percent.replace("-", "")}%`;
  return `${percent}%`;
}

export function formatPercent(percent: string | null): string {
  return percent === null ? "—" : `${percent}%`;
}

const DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** ISO date (YYYY-MM-DD) as "1 Jan 2027". */
export function formatDate(isoDate: string): string {
  return DATE.format(new Date(`${isoDate}T00:00:00Z`));
}

export const REASON_LABELS: Record<ChangeReason, string> = {
  hire: "Hire",
  promotion: "Promotion",
  merit: "Merit increase",
  market_adjustment: "Market adjustment",
  transfer: "Transfer",
  correction: "Correction",
};

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contractor: "Contractor",
};

export const STATUS_LABELS: Record<EmploymentStatus, string> = {
  active: "Active",
  on_leave: "On leave",
  terminated: "Terminated",
};

export function employmentLabel(type: EmploymentType, fte: string): string {
  if (type !== "part_time") return EMPLOYMENT_TYPE_LABELS[type];
  return `Part-time · ${Math.round(Number(fte) * 100)}%`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}
