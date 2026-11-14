import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EmployeeSearch } from "./employee-search";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function renderSearch() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <EmployeeSearch />
    </QueryClientProvider>,
  );
}

describe("EmployeeSearch shortcut", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 8 }),
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("opens with Cmd+K or Ctrl+K", async () => {
    renderSearch();

    fireEvent.keyDown(window, { key: "k", metaKey: true });

    expect(await screen.findByRole("dialog", { name: "Find an employee" })).toBeInTheDocument();
  });

  it("ignores key events without a key, such as those sent by browser autofill", () => {
    renderSearch();

    expect(() =>
      window.dispatchEvent(new Event("keydown", { bubbles: true }) as KeyboardEvent),
    ).not.toThrow();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
