"use client";

import { SearchIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { DEFAULT_FILTERS } from "@/lib/filters";
import { useEmployees } from "@/lib/queries";
import type { EmployeeSummary } from "@/lib/types";
import { useDebounced } from "@/lib/use-debounced";

function optionValue(employee: EmployeeSummary): string {
  return `${employee.employee_code} ${employee.name}`;
}

/** ⌘K (Ctrl+K) finds anyone by name or employee code, from any page. */
export function EmployeeSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const q = useDebounced(query.trim(), 300);
  const results = useEmployees({ ...DEFAULT_FILTERS, q }, 8);
  const items = q ? (results.data?.items ?? []) : [];
  const firstValue = items[0] ? optionValue(items[0]) : "";
  // Results arrive after typing, so highlight the first one ourselves; Enter then opens it.
  const [selected, setSelected] = useState("");
  useEffect(() => setSelected(firstValue), [firstValue]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      // Browser autofill and password managers can send keydown events with no key.
      if (event.key?.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function go(id: number) {
    setOpen(false);
    setQuery("");
    router.push(`/employees/${id}`);
  }

  return (
    <>
      <button
        type="button"
        aria-label="Search employees by name or ID (Command K)"
        aria-keyshortcuts="Meta+K Control+K"
        onClick={() => setOpen(true)}
        className="flex h-10 max-w-[520px] flex-[1_1_320px] items-center gap-2.5 rounded-[10px] border bg-background px-3 text-left text-sm text-muted-foreground hover:border-input"
      >
        <SearchIcon aria-hidden="true" className="size-4" />
        <span className="flex-1">Search employees by name or ID</span>
        <kbd className="amount rounded-md border border-input bg-card px-1.5 py-0.5 text-[11px]">
          ⌘K
        </kbd>
      </button>
      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Find an employee"
        description="Search by name or employee code"
      >
        <Command shouldFilter={false} value={selected} onValueChange={setSelected}>
          <CommandInput
          placeholder="Name or employee code, e.g. Ravi or EMP-04821"
          value={query}
          onValueChange={setQuery}
        />
        <CommandList>
          {q && !results.isFetching ? <CommandEmpty>No one matches “{q}”.</CommandEmpty> : null}
          {items.length ? (
            <CommandGroup heading="Employees">
              {items.map((employee) => (
                <CommandItem
                  key={employee.id}
                  value={optionValue(employee)}
                  onSelect={() => go(employee.id)}
                >
                  <span className="flex-1">
                    <span className="font-medium">{employee.name}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      · {employee.role ? `${employee.role.title} L${employee.role.level}` : "No role"}
                      {employee.country ? ` · ${employee.country.name}` : ""}
                    </span>
                  </span>
                  <span className="amount text-xs text-muted-foreground">
                    {employee.employee_code}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          ) : null}
        </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
