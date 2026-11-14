"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CheckIcon } from "lucide-react";
import Link from "next/link";
import { use, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PreviewPanel } from "@/features/revise/preview-panel";
import {
  confirmationSummary,
  defaultEffectiveDate,
  nextLevelRole,
  raiseBy,
  revisionBody,
  variableDefault,
} from "@/features/revise/model";
import { ApiError } from "@/lib/api";
import { currencySymbol, formatDate, formatMoney, groupNumber, REASON_LABELS } from "@/lib/format";
import { useEmployee, usePayBands, usePreview, useRevise, useRoles } from "@/lib/queries";
import { revisionSchema, type Revision, type RevisionValues } from "@/lib/schemas";
import type { EmployeeProfile, HistoryEntry, Role } from "@/lib/types";
import { useDebounced } from "@/lib/use-debounced";

const REASONS = ["promotion", "merit", "market_adjustment", "correction"] as const;

function ReviseForm({ profile, roles }: { profile: EmployeeProfile; roles: Role[] }) {
  const pkg = profile.package;
  const currentRole = profile.role;
  const next = currentRole ? nextLevelRole(roles, currentRole) : undefined;
  const currentVariable = pkg?.components.find((c) => c.type === "bonus" || c.type === "commission");
  const currency = profile.currency ?? "USD";

  const [promote, setPromote] = useState(Boolean(next));
  const [step, setStep] = useState<"edit" | "confirm" | "done">("edit");
  const [saved, setSaved] = useState<HistoryEntry | null>(null);
  const revise = useRevise(profile.id);

  const startBonus = (promote ? variableDefault(next)?.percent : undefined) ?? (currentVariable?.percent ? String(Number(currentVariable.percent)) : "");
  const form = useForm<RevisionValues, unknown, Revision>({
    resolver: zodResolver(revisionSchema),
    mode: "onChange",
    defaultValues: {
      reason: next ? "promotion" : "merit",
      effectiveFrom: defaultEffectiveDate(),
      baseAnnual: pkg ? groupNumber(raiseBy(pkg.base_salary, 12), currency) : "",
      bonusPercent: startBonus,
      note: "",
    },
  });
  const { errors } = form.formState;
  const watched = useWatch({ control: form.control });
  const roleId = promote && next ? next.id : null;
  const targetRole = promote && next ? next : roles.find((r) => r.id === currentRole?.id);
  const bands = usePayBands(targetRole?.id ?? null, profile.country?.code ?? null);
  const band = bands.data?.[0];

  // Only previews valid input; the debounce keeps typing from firing a request per key.
  const parsed = revisionSchema.safeParse(watched);
  const body = parsed.success
    ? revisionBody(parsed.data, {
        pkg,
        roleId,
        variable: promote ? (variableDefault(next) ?? undefined) : undefined,
      })
    : null;
  const debouncedBody = useDebounced(body, 300);
  const preview = usePreview(profile.id, step === "done" ? null : debouncedBody);
  const previewError =
    preview.error instanceof ApiError ? preview.error.message : preview.error ? "The preview couldn't be worked out." : null;

  const summary = useMemo(
    () =>
      preview.data && parsed.success
        ? confirmationSummary(preview.data, parsed.data, Boolean(roleId))
        : "",
    [preview.data, parsed.success, parsed.data, roleId],
  );

  function togglePromote(checked: boolean) {
    setPromote(checked);
    const defaults = variableDefault(checked ? next : roles.find((r) => r.id === currentRole?.id));
    form.setValue("bonusPercent", defaults?.percent ?? (currentVariable?.percent ? String(Number(currentVariable.percent)) : ""), {
      shouldValidate: true,
    });
    if (checked) form.setValue("reason", "promotion", { shouldValidate: true });
    setStep("edit");
  }

  function pick(units: number) {
    form.setValue("baseAnnual", groupNumber(units, currency), { shouldValidate: true });
    setStep("edit");
  }

  async function confirm() {
    if (!body) return;
    try {
      const entry = await revise.mutateAsync(body);
      setSaved(entry);
      setStep("done");
      toast.success(`Compensation updated · effective ${formatDate(entry.effective_from)}`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "That didn't save. Try again in a moment.");
      setStep("edit");
    }
  }

  const firstName = profile.name.split(" ")[0];
  const nextDefault = variableDefault(next);
  const currentDefault = variableDefault(roles.find((r) => r.id === currentRole?.id));

  return (
    <>
      {step === "done" && saved ? (
        <div
          role="status"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#CFE0D5] bg-[#EEF5F0] px-5 py-4"
        >
          <span className="flex items-center gap-2.5 text-sm text-[#2C4D3A]">
            <CheckIcon aria-hidden="true" className="size-[18px] text-[#3E6A51]" />
            <span>
              <b>Compensation updated.</b>{" "}
              {saved.state === "pending"
                ? `Takes effect ${formatDate(saved.effective_from)}; it shows as pending until then.`
                : `In force from ${formatDate(saved.effective_from)}.`}
            </span>
          </span>
          <Link href={`/employees/${profile.id}`} className="text-sm font-semibold">
            Back to {firstName}&apos;s profile
          </Link>
        </div>
      ) : null}

      <div className="flex flex-col gap-1.5">
        <h1 className="text-[26px] font-semibold tracking-tight">Revise compensation</h1>
        <p className="text-sm text-muted-foreground">
          {profile.name}
          {currentRole ? ` · ${currentRole.title} L${currentRole.level}` : ""}
          {profile.country ? ` · ${profile.country.name}` : ""}
          {pkg ? ` · current base ${formatMoney(pkg.base_salary)}` : ""}
        </p>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(400px,1fr))] items-start gap-5">
        <form
          aria-labelledby="change"
          onSubmit={form.handleSubmit(() => setStep("confirm"))}
          className="flex flex-col gap-5 rounded-xl border bg-card p-6"
        >
          <h2 id="change" className="text-base font-semibold">
            The change
          </h2>
          <fieldset disabled={step === "done"} className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="reason">Reason</Label>
                <Select
                  value={watched.reason}
                  onValueChange={(value) => {
                    form.setValue("reason", value as Revision["reason"], { shouldValidate: true });
                    setStep("edit");
                  }}
                >
                  <SelectTrigger id="reason" className="h-11 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {REASONS.map((reason) => (
                      <SelectItem key={reason} value={reason}>
                        {REASON_LABELS[reason]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="effective">Effective from</Label>
                <Input id="effective" type="date" className="h-11" {...form.register("effectiveFrom", { onChange: () => setStep("edit") })} />
                {errors.effectiveFrom ? <p role="alert" className="text-[13px] text-rose-text">{errors.effectiveFrom.message}</p> : null}
              </div>
            </div>

            {next ? (
              <div className="flex items-start gap-3 rounded-[10px] border p-3.5">
                <Checkbox
                  id="promote"
                  checked={promote}
                  onCheckedChange={(checked) => togglePromote(checked === true)}
                  aria-describedby="promote-hint"
                  className="mt-0.5"
                />
                <span className="flex flex-col gap-0.5">
                  <Label htmlFor="promote" className="cursor-pointer text-sm font-medium">
                    Promote to {next.title} L{next.level}
                  </Label>
                  <span id="promote-hint" className="text-[13px] text-muted-foreground">
                    {nextDefault
                      ? `Applies the L${next.level} defaults: ${nextDefault.type === "commission" ? "commission" : "annual bonus"} target ${nextDefault.percent}%${currentDefault ? ` (was ${currentDefault.percent}%)` : ""}. You can override it below.`
                      : `Moves ${firstName} to the L${next.level} role and band.`}
                  </span>
                </span>
              </div>
            ) : null}

            <div className="flex flex-col gap-2">
              <Label htmlFor="base">New annual base salary ({currency})</Label>
              <div className="flex h-11 items-center gap-2 rounded-[10px] border border-input bg-card px-3 focus-within:border-primary focus-within:ring-3 focus-within:ring-ring/30">
                <span aria-hidden="true" className="text-muted-foreground">
                  {currencySymbol(currency)}
                </span>
                <input
                  id="base"
                  inputMode="numeric"
                  autoComplete="off"
                  aria-invalid={Boolean(errors.baseAnnual)}
                  className="amount min-w-0 flex-1 bg-transparent text-[15px] outline-none"
                  {...form.register("baseAnnual", { onChange: () => setStep("edit") })}
                />
              </div>
              {errors.baseAnnual ? <p role="alert" className="text-[13px] text-rose-text">{errors.baseAnnual.message}</p> : null}
              <div className="flex flex-wrap gap-2">
                {pkg ? (
                  <Button type="button" variant="outline" size="sm" onClick={() => pick(raiseBy(pkg.base_salary, 12))}>
                    +12%
                  </Button>
                ) : null}
                {band ? (
                  <>
                    <Button type="button" variant="outline" size="sm" onClick={() => pick(band.minimum.amount_minor / 100)}>
                      Band minimum
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={() => pick(band.midpoint.amount_minor / 100)}>
                      Band midpoint
                    </Button>
                  </>
                ) : null}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="bonus">
                {(promote ? nextDefault?.type : currentVariable?.type) === "commission"
                  ? "Commission target (% of base)"
                  : "Annual bonus target (% of base)"}
              </Label>
              <Input
                id="bonus"
                inputMode="decimal"
                className="amount h-11 text-[15px]"
                aria-invalid={Boolean(errors.bonusPercent)}
                aria-describedby="bonus-hint"
                {...form.register("bonusPercent", { onChange: () => setStep("edit") })}
              />
              {errors.bonusPercent ? (
                <p role="alert" className="text-[13px] text-rose-text">
                  {errors.bonusPercent.message}
                </p>
              ) : (
                <p id="bonus-hint" className="text-[13px] text-muted-foreground">
                  Leave empty for no variable pay.
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="note">
                Note <span className="font-normal text-muted-foreground">(optional, saved with the history)</span>
              </Label>
              <Input id="note" className="h-11" {...form.register("note")} />
              {errors.note ? <p role="alert" className="text-[13px] text-rose-text">{errors.note.message}</p> : null}
            </div>
          </fieldset>
          {/* Lets Enter in a field move to the review step. */}
          <button type="submit" hidden aria-hidden="true" tabIndex={-1} />
        </form>

        <PreviewPanel
          preview={preview.data}
          error={previewError}
          loading={preview.isFetching}
          countryName={profile.country?.name ?? ""}
        >
          {step === "edit" ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="outline" asChild className="h-11 px-4">
                <Link href={`/employees/${profile.id}`} className="text-foreground hover:text-foreground">
                  Cancel
                </Link>
              </Button>
              <Button
                type="button"
                className="h-11 px-5 font-semibold"
                disabled={!parsed.success || !preview.data || Boolean(previewError) || preview.isFetching}
                onClick={() => setStep("confirm")}
              >
                Review change
              </Button>
            </div>
          ) : null}
          {step === "confirm" ? (
            <div role="dialog" aria-labelledby="confirm-title" className="flex flex-col gap-3 rounded-xl border-2 border-primary bg-[#FAFAFE] p-4">
              <h3 id="confirm-title" className="text-[15px] font-semibold">
                Confirm this change for {profile.name}
              </h3>
              <p className="text-sm leading-relaxed text-subtle-foreground">{summary}</p>
              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="outline" className="h-11 px-4" onClick={() => setStep("edit")}>
                  Go back
                </Button>
                <Button className="h-11 px-5 font-semibold" disabled={revise.isPending} onClick={confirm} autoFocus>
                  {revise.isPending ? "Saving…" : "Confirm & save"}
                </Button>
              </div>
            </div>
          ) : null}
        </PreviewPanel>
      </div>
    </>
  );
}

export default function RevisePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const employee = useEmployee(Number(id));
  const roles = useRoles();

  if (employee.isError) return <ErrorState error={employee.error} onRetry={() => employee.refetch()} />;
  if (!employee.data || !roles.data) return <LoadingRows rows={8} />;
  if (employee.data.status === "terminated") {
    return (
      <ErrorState error={new ApiError(409, "EMPLOYEE_TERMINATED", `${employee.data.name} has left, so their pay can't be changed.`)} />
    );
  }
  return (
    <>
      <nav aria-label="Breadcrumb" className="-mb-2 text-[13px] text-muted-foreground">
        <Link href="/employees">Employees</Link> / <Link href={`/employees/${employee.data.id}`}>{employee.data.name}</Link> /{" "}
        <span>Revise compensation</span>
      </nav>
      <ReviseForm profile={employee.data} roles={roles.data} />
    </>
  );
}
