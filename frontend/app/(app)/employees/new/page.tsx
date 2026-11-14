"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { BandGauge } from "@/components/band-gauge";
import { PageHeading, Panel } from "@/components/page-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { currencySymbol, EMPLOYMENT_TYPE_LABELS, majorToMinor } from "@/lib/format";
import { useCountries, useHire, usePayBands, useRoles } from "@/lib/queries";
import { hireSchema, type Hire, type HireValues } from "@/lib/schemas";
import type { BandPosition, EmploymentType, Role } from "@/lib/types";

function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error ? (
        <p role="alert" className="text-[13px] text-rose-text">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function byDepartment(roles: Role[]): [string, Role[]][] {
  const groups = new Map<string, Role[]>();
  for (const role of roles) groups.set(role.department, [...(groups.get(role.department) ?? []), role]);
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export default function HirePage() {
  const router = useRouter();
  const countries = useCountries();
  const roles = useRoles();
  const hire = useHire();
  const [bonusOverride, setBonusOverride] = useState("");
  const [failure, setFailure] = useState<string | null>(null);

  const form = useForm<HireValues, unknown, Hire>({
    resolver: zodResolver(hireSchema),
    defaultValues: {
      employeeCode: "",
      name: "",
      email: "",
      countryCode: "",
      roleId: "",
      employmentType: "full_time",
      fte: "1",
      hireDate: "",
      baseAnnual: "",
    },
  });
  const { errors, isSubmitting } = form.formState;
  const values = useWatch({ control: form.control });
  const role = roles.data?.find((r) => String(r.id) === values.roleId);
  const country = countries.data?.find((c) => c.code === values.countryCode);
  const bands = usePayBands(role?.id ?? null, country?.code ?? null);
  const band = bands.data?.[0];
  const defaultVariable = role?.defaults.find((d) => d.type === "bonus" || d.type === "commission");

  // Indicative only, to check an offer while typing; the server makes the real comparison after hiring.
  const base = Number(String(values.baseAnnual ?? "").replace(/[,\s]/g, ""));
  const fte = Number(values.fte) || 1;
  const offer = band && base > 0 && values.employmentType !== "contractor"
    ? { amount_minor: majorToMinor(base / fte), currency: band.minimum.currency }
    : null;
  const position: BandPosition | null = offer && band
    ? offer.amount_minor < band.minimum.amount_minor
      ? "below"
      : offer.amount_minor > band.maximum.amount_minor
        ? "above"
        : "in_band"
    : null;

  async function onSubmit(hireValues: Hire) {
    setFailure(null);
    const override = bonusOverride.trim();
    const overridePercent = Number(override);
    if (override && !(overridePercent >= 0 && overridePercent <= 100)) {
      setFailure("Enter a bonus between 0% and 100%.");
      return;
    }
    try {
      const profile = await hire.mutateAsync({
        employee_code: hireValues.employeeCode,
        name: hireValues.name,
        email: hireValues.email,
        country_code: hireValues.countryCode,
        role_id: Number(hireValues.roleId),
        employment_type: hireValues.employmentType,
        fte: String(hireValues.fte),
        hire_date: hireValues.hireDate,
        base_annual_minor: majorToMinor(hireValues.baseAnnual),
        ...(override && defaultVariable
          ? {
              components:
                overridePercent > 0
                  ? [{ type: defaultVariable.type, basis: "percent_of_base", frequency: "annual", label: defaultVariable.label, percent: override }]
                  : [],
            }
          : {}),
      });
      toast.success(`${profile.name} added.`);
      router.push(`/employees/${profile.id}`);
    } catch (error) {
      setFailure(error instanceof ApiError ? error.message : "That didn't save. Try again in a moment.");
    }
  }

  const type = values.employmentType as EmploymentType;

  return (
    <>
      <nav aria-label="Breadcrumb" className="-mb-2 text-[13px] text-muted-foreground">
        <Link href="/employees">Employees</Link> / <span>Add employee</span>
      </nav>
      <PageHeading title="Add employee">
        Pick the role and country first: the role&apos;s default pay structure is applied, and you can check the offer
        against the band before saving.
      </PageHeading>

      <form noValidate onSubmit={form.handleSubmit(onSubmit)} className="grid grid-cols-[repeat(auto-fit,minmax(400px,1fr))] items-start gap-5">
        <Panel title="Employee" id="employee">
          {failure ? (
            <p role="alert" className="rounded-[10px] bg-rose-tint px-3.5 py-3 text-[13px] text-rose-text">
              {failure}
            </p>
          ) : null}
          <div className="grid grid-cols-2 gap-4">
            <Field id="code" label="Employee code" error={errors.employeeCode?.message}>
              <Input id="code" placeholder="EMP-10001" {...form.register("employeeCode")} />
            </Field>
            <Field id="hire-date" label="Hire date" error={errors.hireDate?.message}>
              <Input id="hire-date" type="date" {...form.register("hireDate")} />
            </Field>
          </div>
          <Field id="name" label="Full name" error={errors.name?.message}>
            <Input id="name" autoComplete="off" {...form.register("name")} />
          </Field>
          <Field id="email" label="Work email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="off" {...form.register("email")} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field id="type" label="Employment type">
              <Controller
                control={form.control}
                name="employmentType"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      field.onChange(value);
                      form.setValue("fte", value === "part_time" ? "0.5" : "1");
                    }}
                  >
                    <SelectTrigger id="type" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(EMPLOYMENT_TYPE_LABELS) as EmploymentType[]).map((option) => (
                        <SelectItem key={option} value={option}>
                          {EMPLOYMENT_TYPE_LABELS[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
            <Field id="fte" label="FTE" error={errors.fte?.message}>
              <Input id="fte" inputMode="decimal" disabled={type !== "part_time"} {...form.register("fte")} />
            </Field>
          </div>
        </Panel>

        <Panel title="Role and pay" id="pay">
          <div className="grid grid-cols-2 gap-4">
            <Field id="country" label="Country" error={errors.countryCode?.message}>
              <Controller
                control={form.control}
                name="countryCode"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="country" className="w-full">
                      <SelectValue placeholder="Choose a country" />
                    </SelectTrigger>
                    <SelectContent>
                      {(countries.data ?? []).map((c) => (
                        <SelectItem key={c.code} value={c.code}>
                          {c.name} · {c.currency}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
            <Field id="role" label="Role" error={errors.roleId?.message}>
              <Controller
                control={form.control}
                name="roleId"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="role" className="w-full">
                      <SelectValue placeholder="Choose a role" />
                    </SelectTrigger>
                    <SelectContent className="max-h-80">
                      {byDepartment(roles.data ?? []).map(([department, list]) => (
                        <SelectGroup key={department}>
                          <SelectLabel>{department}</SelectLabel>
                          {list.map((r) => (
                            <SelectItem key={r.id} value={String(r.id)}>
                              {r.title} L{r.level}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
          </div>

          <Field id="base" label={`Annual base salary${country ? ` (${country.currency})` : ""}`} error={errors.baseAnnual?.message}>
            <div className="flex h-9 items-center gap-2 rounded-md border border-input bg-card px-3 focus-within:border-primary">
              <span aria-hidden="true" className="text-muted-foreground">
                {country ? currencySymbol(country.currency) : ""}
              </span>
              <input id="base" inputMode="numeric" className="amount min-w-0 flex-1 bg-transparent outline-none" {...form.register("baseAnnual")} />
            </div>
          </Field>

          {role ? (
            <div className="flex flex-col gap-2 rounded-[10px] border p-3.5 text-[13px]">
              <span className="font-medium">
                {defaultVariable
                  ? `${role.title} L${role.level} default: ${defaultVariable.label.toLowerCase()} ${Number(defaultVariable.percent)}% of base`
                  : `${role.title} L${role.level} has no default variable pay`}
              </span>
              {defaultVariable && type !== "contractor" ? (
                <div className="flex items-center gap-2">
                  <Label htmlFor="bonus-override" className="font-normal text-muted-foreground">
                    Override (%)
                  </Label>
                  <Input
                    id="bonus-override"
                    inputMode="decimal"
                    className="amount h-8 w-24"
                    placeholder={String(Number(defaultVariable.percent))}
                    value={bonusOverride}
                    onChange={(event) => setBonusOverride(event.target.value)}
                  />
                  <span className="text-muted-foreground">Leave empty to use the default; 0 for none.</span>
                </div>
              ) : null}
            </div>
          ) : null}

          {band && offer && position ? (
            <div className="flex flex-col gap-2">
              <span className="text-sm font-medium">
                Offer against the {role?.title} L{role?.level} band{type === "part_time" ? " (at full-time equivalent)" : ""}
              </span>
              <BandGauge band={band} value={offer} position={position} />
              {position !== "in_band" ? (
                <p className="text-[13px] text-amber-text">
                  {position === "below" ? "▼ Below the band minimum." : "▲ Above the band maximum."} You can still save it; it will show in
                  Exceptions.
                </p>
              ) : null}
            </div>
          ) : type === "contractor" ? (
            <p className="text-[13px] text-muted-foreground">Contractors aren&apos;t banded.</p>
          ) : null}

          <div className="flex justify-end gap-2">
            <Button variant="outline" asChild>
              <Link href="/employees" className="text-foreground hover:text-foreground">
                Cancel
              </Link>
            </Button>
            <Button type="submit" disabled={isSubmitting || hire.isPending} className="font-semibold">
              {hire.isPending ? "Adding…" : "Add employee"}
            </Button>
          </div>
        </Panel>
      </form>
    </>
  );
}
