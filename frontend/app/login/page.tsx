"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircleIcon, LockIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { loginSchema } from "@/lib/schemas";
import type { z } from "zod";

type LoginValues = z.infer<typeof loginSchema>;

/** Only same-site paths, so a crafted ?next= can't send someone elsewhere after sign-in. */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [failure, setFailure] = useState<string | null>(null);
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: LoginValues) {
    setFailure(null);
    try {
      await api.post("/auth/login", values);
      router.replace(safeNext(params.get("next")));
    } catch (error) {
      setFailure(
        error instanceof ApiError && error.code === "INVALID_CREDENTIALS"
          ? error.message
          : "We couldn't sign you in just now. Try again in a moment.",
      );
    }
  }

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="flex w-full max-w-[400px] flex-col gap-6"
    >
      <div className="flex flex-col gap-2">
        <h2 className="text-[28px] font-semibold tracking-tight">Sign in</h2>
        <p className="text-sm text-muted-foreground">Use the HR Manager account set up for ACME.</p>
      </div>

      {failure ? (
        <div
          role="alert"
          className="flex items-center gap-2.5 rounded-[10px] bg-rose-tint px-3.5 py-2.5 text-[13px] text-rose-text"
        >
          <AlertCircleIcon aria-hidden="true" className="size-4 shrink-0" />
          <span>{failure}</span>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Work email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="username"
          className="h-11 bg-card"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...form.register("email")}
        />
        {errors.email ? (
          <p id="email-error" className="text-[13px] text-rose-text">
            {errors.email.message}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          className="h-11 bg-card"
          aria-invalid={Boolean(errors.password)}
          aria-describedby={errors.password ? "password-error" : undefined}
          {...form.register("password")}
        />
        {errors.password ? (
          <p id="password-error" className="text-[13px] text-rose-text">
            {errors.password.message}
          </p>
        ) : null}
      </div>

      <Button type="submit" className="h-11 font-semibold" disabled={isSubmitting}>
        {isSubmitting ? "Signing in…" : "Sign in"}
      </Button>

      <div
        role="note"
        className="flex items-start gap-2.5 rounded-[10px] border bg-card px-3.5 py-3 text-[13px] leading-normal text-muted-foreground"
      >
        <LockIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span>Salary data is confidential. Sessions end after 8 hours or when you sign out.</span>
      </div>
    </form>
  );
}

const FACTS = [
  ["10,000", "employees"],
  ["8", "countries"],
  ["125", "roles & levels"],
] as const;

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-wrap bg-background">
      <section className="flex min-w-0 flex-[1_1_480px] flex-col justify-between gap-12 bg-foreground px-8 py-14 text-[#ECEDEF] sm:px-16">
        <Logo size="lg" />
        <div className="flex max-w-[460px] flex-col gap-5">
          <h1 className="text-[40px] leading-[1.15] font-semibold tracking-tight">
            Every salary, with the context to trust it.
          </h1>
          <p className="text-base leading-relaxed text-[#B4B9C2]">
            Manage pay for 10,000 people across 8 countries. See each package against its band,
            record changes with a reason and a date, and answer leadership&apos;s questions in
            minutes.
          </p>
        </div>
        <dl className="grid max-w-[520px] grid-cols-3 gap-4">
          {FACTS.map(([value, label]) => (
            <div key={label} className="flex flex-col gap-1 border-t border-[#343944] pt-3">
              <dd className="amount text-xl">{value}</dd>
              <dt className="order-last text-xs text-[#9BA1AC]">{label}</dt>
            </div>
          ))}
        </dl>
      </section>
      <main className="flex min-w-0 flex-[1_1_480px] items-center justify-center px-6 py-14">
        <Suspense>
          <LoginForm />
        </Suspense>
      </main>
    </div>
  );
}
