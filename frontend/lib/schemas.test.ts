import { describe, expect, it } from "vitest";

import { hireSchema, loginSchema, revisionSchema } from "./schemas";

function messages(result: { success: boolean; error?: { issues: { message: string }[] } }) {
  return result.success ? [] : (result.error?.issues.map((issue) => issue.message) ?? []);
}

describe("login", () => {
  it("needs an email and a password", () => {
    expect(messages(loginSchema.safeParse({ email: "", password: "" }))).toEqual([
      "Enter your work email.",
      "Enter your password.",
    ]);
  });

  it("checks the email looks like one", () => {
    expect(messages(loginSchema.safeParse({ email: "meera", password: "x" }))).toEqual([
      "Enter a work email such as name@company.com.",
    ]);
  });
});

describe("revision", () => {
  const valid = {
    reason: "promotion",
    effectiveFrom: "2027-01-01",
    baseAnnual: "2688000",
    bonusPercent: "15",
    note: "",
  };

  it("accepts a promotion with a 15% bonus", () => {
    expect(revisionSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects a bonus outside 0% to 100%, mirroring the server (E21)", () => {
    expect(messages(revisionSchema.safeParse({ ...valid, bonusPercent: "150" }))).toEqual([
      "Enter a bonus between 0% and 100%.",
    ]);
  });

  it("treats an empty bonus as no bonus", () => {
    const parsed = revisionSchema.parse({ ...valid, bonusPercent: "" });

    expect(parsed.bonusPercent).toBeNull();
  });

  it("rejects a zero or missing base salary (E20)", () => {
    expect(messages(revisionSchema.safeParse({ ...valid, baseAnnual: "0" }))).toEqual([
      "Enter a base salary above zero.",
    ]);
    expect(messages(revisionSchema.safeParse({ ...valid, baseAnnual: "" }))).toEqual([
      "Enter a base salary above zero.",
    ]);
  });

  it("accepts grouped numbers as typed, such as 26,88,000", () => {
    expect(revisionSchema.parse({ ...valid, baseAnnual: "26,88,000" }).baseAnnual).toBe(2_688_000);
  });

  it("needs an effective date", () => {
    expect(messages(revisionSchema.safeParse({ ...valid, effectiveFrom: "" }))).toEqual([
      "Choose the date the change takes effect.",
    ]);
  });

  it("keeps notes short enough for history", () => {
    expect(messages(revisionSchema.safeParse({ ...valid, note: "x".repeat(501) }))).toEqual([
      "Keep the note under 500 characters.",
    ]);
  });
});

describe("hire", () => {
  const valid = {
    employeeCode: "EMP-09121",
    name: "Sneha Patil",
    email: "sneha@acme.example",
    countryCode: "IN",
    roleId: "3",
    employmentType: "full_time",
    fte: "1",
    hireDate: "2026-07-08",
    baseAnnual: "980000",
  };

  it("accepts a full-time hire", () => {
    expect(hireSchema.safeParse(valid).success).toBe(true);
  });

  it("matches FTE to the employment type, as the server does", () => {
    expect(messages(hireSchema.safeParse({ ...valid, fte: "0.6" }))).toEqual([
      "Full-time is 1.0 FTE; part-time is between 0 and 1.",
    ]);
    expect(
      hireSchema.safeParse({ ...valid, employmentType: "part_time", fte: "0.6" }).success,
    ).toBe(true);
    expect(messages(hireSchema.safeParse({ ...valid, employmentType: "part_time" }))).toEqual([
      "Full-time is 1.0 FTE; part-time is between 0 and 1.",
    ]);
  });

  it("needs a role and a country", () => {
    expect(messages(hireSchema.safeParse({ ...valid, roleId: "", countryCode: "" }))).toEqual([
      "Choose a country.",
      "Choose a role.",
    ]);
  });
});
