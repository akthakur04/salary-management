import { z } from "zod";

/**
 * Form rules that mirror the server's (domain and Pydantic), for instant
 * feedback. The server stays the source of truth and still validates.
 */

export const loginSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your work email.")
    .refine((value) => value === "" || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value), {
      message: "Enter a work email such as name@company.com.",
    }),
  password: z.string().min(1, "Enter your password."),
});

/** Whole local currency units, as typed: "26,88,000" or "2688000". */
const amount = (message: string) =>
  z
    .string()
    .transform((value) => Number(value.replace(/[,\s]/g, "")))
    .refine((value) => Number.isFinite(value) && value > 0, message);

export const REVISION_REASONS = [
  "promotion",
  "merit",
  "market_adjustment",
  "transfer",
  "correction",
] as const;

export const revisionSchema = z.object({
  reason: z.enum(REVISION_REASONS),
  effectiveFrom: z.string().min(1, "Choose the date the change takes effect."),
  baseAnnual: amount("Enter a base salary above zero."),
  bonusPercent: z
    .string()
    .transform((value) => (value.trim() === "" ? null : Number(value)))
    .refine(
      (value) => value === null || (Number.isFinite(value) && value >= 0 && value <= 100),
      "Enter a bonus between 0% and 100%.",
    ),
  note: z.string().max(500, "Keep the note under 500 characters."),
});

export type RevisionValues = z.input<typeof revisionSchema>;
export type Revision = z.output<typeof revisionSchema>;

export const hireSchema = z
  .object({
    employeeCode: z.string().trim().min(1, "Enter an employee code.").max(20),
    name: z.string().trim().min(1, "Enter the employee's name.").max(120),
    email: loginSchema.shape.email,
    countryCode: z.string().min(1, "Choose a country."),
    roleId: z.string().min(1, "Choose a role."),
    employmentType: z.enum(["full_time", "part_time", "contractor"]),
    fte: z.string().transform(Number),
    hireDate: z.string().min(1, "Choose the hire date."),
    baseAnnual: amount("Enter a base salary above zero."),
  })
  .superRefine((values, context) => {
    const valid =
      values.employmentType === "full_time"
        ? values.fte === 1
        : values.employmentType === "part_time"
          ? values.fte > 0 && values.fte < 1
          : values.fte > 0 && values.fte <= 1;
    if (!valid) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["fte"],
        message: "Full-time is 1.0 FTE; part-time is between 0 and 1.",
      });
    }
  });

export type HireValues = z.input<typeof hireSchema>;
export type Hire = z.output<typeof hireSchema>;
