import { describe, expect, it } from "vitest";

import {
  formatChange,
  formatCompactUsd,
  formatDate,
  formatMoney,
  formatPercent,
  majorToMinor,
  minorToMajor,
} from "./format";

describe("formatMoney", () => {
  it("uses Indian lakh grouping for rupees", () => {
    expect(formatMoney({ amount_minor: 2_400_000_00, currency: "INR" })).toBe("₹24,00,000");
  });

  it("uses the currency's own symbol", () => {
    expect(formatMoney({ amount_minor: 118_000_00, currency: "EUR" })).toBe("€118,000");
    expect(formatMoney({ amount_minor: 58_500_00, currency: "GBP" })).toBe("£58,500");
    expect(formatMoney({ amount_minor: 66_000_00, currency: "SGD" })).toBe("S$66,000");
    expect(formatMoney({ amount_minor: 84_000_00, currency: "BRL" })).toBe("R$84,000");
    expect(formatMoney({ amount_minor: 171_000_00, currency: "CAD" })).toBe("C$171,000");
    expect(formatMoney({ amount_minor: 158_000_00, currency: "AUD" })).toBe("A$158,000");
    expect(formatMoney({ amount_minor: 36_316_80, currency: "USD" })).toBe("$36,317");
  });

  it("can show cents when they matter", () => {
    expect(formatMoney({ amount_minor: 36_316_80, currency: "USD" }, { cents: true })).toBe(
      "$36,316.80",
    );
  });

  it("writes negative amounts with a true minus sign", () => {
    expect(formatMoney({ amount_minor: -90_000_00, currency: "INR" })).toBe("−₹90,000");
  });

  it("shows an unknown currency by its code", () => {
    expect(formatMoney({ amount_minor: 1_000_00, currency: "JPY" })).toBe("JPY 1,000");
  });
});

describe("formatCompactUsd", () => {
  it("abbreviates large totals for KPI cards", () => {
    expect(formatCompactUsd(812_400_000_00)).toBe("$812.4M");
    expect(formatCompactUsd(71_300_00)).toBe("$71.3K");
  });
});

describe("percentages", () => {
  it("formats a change with its sign", () => {
    expect(formatChange("12.0")).toBe("+12.0%");
    expect(formatChange("-1.2")).toBe("−1.2%");
    expect(formatChange("0.0")).toBe("0.0%");
    expect(formatChange(null)).toBe("—");
  });

  it("formats a share", () => {
    expect(formatPercent("92.1")).toBe("92.1%");
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("reads like the design: day, short month, year", () => {
    expect(formatDate("2027-01-01")).toBe("1 Jan 2027");
    expect(formatDate("2026-11-12")).toBe("12 Nov 2026");
  });
});

describe("minor and major units", () => {
  it("converts whole local amounts to minor units and back", () => {
    expect(majorToMinor(2_688_000)).toBe(268_800_000);
    expect(minorToMajor(268_800_000)).toBe(2_688_000);
  });
});
