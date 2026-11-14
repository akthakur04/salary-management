import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "./page";

const replace = vi.fn();
let next: string | null = null;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(next ? { next } : {}),
}));

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({ status, ok: status < 400, json: () => Promise.resolve(body) });
}

async function signIn(email: string, password: string) {
  const user = userEvent.setup();
  if (email) await user.type(screen.getByLabelText("Work email"), email);
  if (password) await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("login page", () => {
  beforeEach(() => {
    replace.mockReset();
    next = null;
  });
  afterEach(() => vi.unstubAllGlobals());

  it("explains what's missing without calling the server", async () => {
    const fetch = respond(200, {});
    vi.stubGlobal("fetch", fetch);
    render(<LoginPage />);

    await signIn("", "");

    expect(await screen.findByText("Enter your work email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Work email")).toHaveAttribute("aria-invalid", "true");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows the server's generic message for wrong credentials", async () => {
    vi.stubGlobal(
      "fetch",
      respond(401, {
        error: {
          code: "INVALID_CREDENTIALS",
          message: "That email and password don't match. Check both and try again.",
          details: {},
        },
      }),
    );
    render(<LoginPage />);

    await signIn("meera.iyer@acme.example", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email and password don't match. Check both and try again.",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("returns to the page that asked for sign-in", async () => {
    next = "/employees?country=IN";
    vi.stubGlobal("fetch", respond(200, { email: "meera.iyer@acme.example" }));
    render(<LoginPage />);

    await signIn("meera.iyer@acme.example", "right");

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/employees?country=IN"));
  });

  it("never follows a next= link to another site", async () => {
    next = "//evil.example/phish";
    vi.stubGlobal("fetch", respond(200, { email: "meera.iyer@acme.example" }));
    render(<LoginPage />);

    await signIn("meera.iyer@acme.example", "right");

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
  });
});
