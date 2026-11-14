import { describe, expect, it } from "vitest";

import type { Package, Preview, Role } from "@/lib/types";

import {
  confirmationSummary,
  defaultEffectiveDate,
  nextLevelRole,
  raiseBy,
  revisionBody,
  variableDefault,
} from "./model";

const inr = (rupees: number) => ({ amount_minor: rupees * 100, currency: "INR" });

const RAVI_PACKAGE: Package = {
  version_id: 4,
  effective_from: "2025-04-01",
  reason: "merit",
  base_salary: inr(24_00_000),
  components: [
    {
      type: "allowance",
      basis: "fixed_amount",
      frequency: "monthly",
      label: "Housing allowance",
      amount: inr(30_000),
      percent: null,
      payout_date: null,
      annual_amount: inr(3_60_000),
    },
    {
      type: "allowance",
      basis: "fixed_amount",
      frequency: "monthly",
      label: "Meal allowance",
      amount: inr(2_200),
      percent: null,
      payout_date: null,
      annual_amount: inr(26_400),
    },
    {
      type: "bonus",
      basis: "percent_of_base",
      frequency: "annual",
      label: "Annual bonus",
      amount: null,
      percent: "10.00",
      payout_date: null,
      annual_amount: inr(2_40_000),
    },
  ],
  fixed_cash: inr(27_86_400),
  target_variable: inr(2_40_000),
  total_target_compensation: inr(30_26_400),
  total_target_compensation_usd: { amount_minor: 3_631_680, currency: "USD" },
  variable_share: "7.9",
};

const role = (id: number, level: number, defaults: Role["defaults"] = []): Role => ({
  id,
  department_id: 1,
  department: "Engineering",
  family: "Software Engineer",
  level,
  title: "Software Engineer",
  defaults,
});

const L3 = role(3, 3, [{ type: "bonus", percent: "10.00", label: "Annual bonus" }]);
const L4 = role(4, 4, [{ type: "bonus", percent: "15.00", label: "Annual bonus" }]);
const L5 = role(5, 5, [{ type: "bonus", percent: "20.00", label: "Annual bonus" }]);

describe("promotion", () => {
  it("finds the next level in the same job family", () => {
    expect(nextLevelRole([L5, L3, L4], { id: 3, title: "Software Engineer", level: 3 })).toBe(L4);
    expect(nextLevelRole([L3, L4, L5], { id: 5, title: "Software Engineer", level: 5 })).toBeUndefined();
  });

  it("uses the new level's default variable pay", () => {
    expect(variableDefault(L4)).toEqual({ type: "bonus", percent: "15", label: "Annual bonus" });
    expect(variableDefault(role(9, 1))).toBeNull();
  });
});

describe("quick picks", () => {
  it("raises by a percentage, rounded to the nearest hundred", () => {
    expect(raiseBy(inr(24_00_000), 12)).toBe(26_88_000);
    expect(raiseBy(inr(24_00_050), 3)).toBe(24_72_100);
  });
});

describe("revisionBody", () => {
  const values = {
    reason: "promotion" as const,
    effectiveFrom: "2027-01-01",
    baseAnnual: 26_88_000,
    bonusPercent: 15,
    note: "  2026 promotion cycle  ",
  };

  it("keeps recurring allowances, applies the bonus override and moves to the new role", () => {
    expect(revisionBody(values, { pkg: RAVI_PACKAGE, roleId: 4 })).toEqual({
      effective_from: "2027-01-01",
      reason: "promotion",
      base_annual_minor: 2_688_000_00,
      role_id: 4,
      components: [
        {
          type: "allowance",
          basis: "fixed_amount",
          frequency: "monthly",
          label: "Housing allowance",
          amount_minor: 30_000_00,
        },
        {
          type: "allowance",
          basis: "fixed_amount",
          frequency: "monthly",
          label: "Meal allowance",
          amount_minor: 2_200_00,
        },
        {
          type: "bonus",
          basis: "percent_of_base",
          frequency: "annual",
          label: "Annual bonus",
          percent: "15",
        },
      ],
      note: "2026 promotion cycle",
    });
  });

  it("removes variable pay when the bonus is empty or zero (E2, E20)", () => {
    for (const bonusPercent of [null, 0]) {
      const body = revisionBody({ ...values, bonusPercent }, { pkg: RAVI_PACKAGE, roleId: null });
      expect(body.components?.map((c) => c.type)).toEqual(["allowance", "allowance"]);
      expect(body.role_id).toBeUndefined();
    }
  });

  it("keeps commission as commission when that is the variable pay", () => {
    const commissioned = {
      ...RAVI_PACKAGE,
      components: [
        { ...RAVI_PACKAGE.components[2], type: "commission" as const, label: "Sales commission" },
      ],
    };

    const body = revisionBody({ ...values, bonusPercent: 45 }, { pkg: commissioned, roleId: null });

    expect(body.components).toEqual([
      {
        type: "commission",
        basis: "percent_of_base",
        frequency: "annual",
        label: "Sales commission",
        percent: "45",
      },
    ]);
  });

  it("leaves the note out when it is blank", () => {
    expect(revisionBody({ ...values, note: "  " }, { pkg: RAVI_PACKAGE, roleId: 4 }).note).toBeUndefined();
  });
});

describe("confirmationSummary", () => {
  it("states the whole change in one sentence, as the design does", () => {
    const preview = {
      before: { total_target_compensation: inr(30_26_400), base_salary: inr(24_00_000) },
      after: {
        role: { id: 4, title: "Software Engineer", level: 4 },
        base_salary: inr(26_88_000),
        total_target_compensation: inr(34_77_600),
      },
      base_change_percent: "12.0",
    } as unknown as Preview;

    expect(
      confirmationSummary(preview, { reason: "promotion", effectiveFrom: "2027-01-01", bonusPercent: 15 }, true),
    ).toBe(
      "Promotion to Software Engineer L4, effective 1 Jan 2027. Base ₹24,00,000 → ₹26,88,000 (+12.0%), bonus target 15%. Total target pay ₹30,26,400 → ₹34,77,600. The current package stays in history.",
    );
  });

  it("leaves out the bonus when there is none", () => {
    const preview = {
      before: { total_target_compensation: inr(100), base_salary: inr(100) },
      after: { role: { id: 3, title: "QA Engineer", level: 2 }, base_salary: inr(110), total_target_compensation: inr(110) },
      base_change_percent: "10.0",
    } as unknown as Preview;

    expect(confirmationSummary(preview, { reason: "merit", effectiveFrom: "2026-12-01", bonusPercent: null }, false)).toBe(
      "Merit increase, effective 1 Dec 2026. Base ₹100 → ₹110 (+10.0%). Total target pay ₹100 → ₹110. The current package stays in history.",
    );
  });
});

describe("defaultEffectiveDate", () => {
  it("is the first day of next month", () => {
    expect(defaultEffectiveDate(new Date("2026-11-14T10:00:00Z"))).toBe("2026-12-01");
    expect(defaultEffectiveDate(new Date("2026-12-31T10:00:00Z"))).toBe("2027-01-01");
  });
});
