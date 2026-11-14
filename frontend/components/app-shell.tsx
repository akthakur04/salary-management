"use client";

import {
  ChartColumnIcon,
  LayoutDashboardIcon,
  TriangleAlertIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { EmployeeSearch } from "@/components/employee-search";
import { Logo } from "@/components/logo";
import { formatDate, initials } from "@/lib/format";
import { useExceptions, useLogout, useMe, useSummary } from "@/lib/queries";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/", label: "Overview", icon: LayoutDashboardIcon },
  { href: "/employees", label: "Employees", icon: UsersIcon },
  { href: "/insights", label: "Insights", icon: ChartColumnIcon },
  { href: "/exceptions", label: "Exceptions", icon: TriangleAlertIcon },
];

/** "meera.iyer@acme.example" → "Meera Iyer". The single login has no name of its own. */
function displayName(email: string): string {
  return email
    .split("@")[0]
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const me = useMe();
  const summary = useSummary();
  const exceptions = useExceptions("below", 1, 1);
  const logout = useLogout();
  const name = me.data ? displayName(me.data.email) : "";
  const badge = exceptions.data?.counts.total;

  async function signOut() {
    await logout.mutateAsync().catch(() => undefined);
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen flex-wrap bg-background">
      <nav
        aria-label="Main"
        className="flex max-w-full flex-[1_1_232px] flex-col gap-6 border-r bg-card px-4 py-5 md:sticky md:top-0 md:h-screen md:max-w-[260px]"
      >
        <Link href="/" className="px-2 py-1 text-foreground hover:text-foreground">
          <Logo />
        </Link>
        <ul className="flex flex-col gap-0.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-10 items-center gap-2.5 rounded-lg px-2.5 text-sm",
                    active
                      ? "bg-primary-tint font-semibold text-primary-strong"
                      : "text-subtle-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  <Icon aria-hidden="true" className="size-4" />
                  <span className="flex-1">{label}</span>
                  {href === "/exceptions" && badge !== undefined ? (
                    <span className="amount rounded-full bg-amber-tint px-2 py-0.5 text-xs text-amber-text">
                      <span className="sr-only">, </span>
                      {badge.toLocaleString("en-US")}
                      <span className="sr-only"> to review</span>
                    </span>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="mt-auto flex items-center gap-2.5 border-t px-2 pt-3">
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-full bg-sage-tint text-xs font-semibold text-sage-text"
          >
            {initials(name)}
          </span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-[13px] font-semibold">{name || " "}</span>
            <span className="text-xs text-muted-foreground">HR Manager</span>
          </span>
          <button
            type="button"
            onClick={signOut}
            className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            Sign out
          </button>
        </div>
      </nav>
      <div className="flex min-w-0 flex-[999_1_560px] flex-col">
        <header className="flex flex-wrap items-center gap-4 border-b bg-card px-8 py-4">
          <EmployeeSearch />
          {summary.data ? (
            <span className="ml-auto text-[13px] text-muted-foreground">
              Figures as of{" "}
              <b className="font-semibold text-foreground">{formatDate(summary.data.as_of)}</b> ·
              USD at reference rates
            </span>
          ) : null}
        </header>
        <main className="flex w-full max-w-[1280px] flex-col gap-6 p-8">{children}</main>
      </div>
    </div>
  );
}
