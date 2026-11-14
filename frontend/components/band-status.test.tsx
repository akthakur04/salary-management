import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BandStatus } from "./band-status";

const inBand = {
  position: "in_band" as const,
  compa_ratio: "0.89",
  fte_equivalent_base: { amount_minor: 2_400_000_00, currency: "INR" },
  gap_to_minimum: null,
};

describe("BandStatus", () => {
  it("shows in band with a dot, the words and the compa-ratio", () => {
    render(<BandStatus band={inBand} />);

    expect(screen.getByText("In band · 0.89")).toBeInTheDocument();
    expect(screen.getByText("●")).toHaveAttribute("aria-hidden", "true");
  });

  it("shows below band in amber with a down triangle, never in red", () => {
    render(<BandStatus band={{ ...inBand, position: "below", compa_ratio: "0.78" }} />);

    const label = screen.getByText("Below band · 0.78");
    expect(screen.getByText("▼")).toBeInTheDocument();
    expect(label.closest("[data-status]")).toHaveAttribute("data-status", "below");
    expect(label.closest("[data-status]")?.className).toContain("amber");
    expect(label.closest("[data-status]")?.className).not.toMatch(/rose|red|destructive/);
  });

  it("shows above band as informational with an up triangle", () => {
    render(<BandStatus band={{ ...inBand, position: "above", compa_ratio: "1.21" }} />);

    expect(screen.getByText("Above band · 1.21")).toBeInTheDocument();
    expect(screen.getByText("▲")).toBeInTheDocument();
  });

  it("shows no band for contractors, with no compa-ratio", () => {
    render(<BandStatus band={{ ...inBand, position: "no_band", compa_ratio: null }} />);

    expect(screen.getByText("No band")).toBeInTheDocument();
    expect(screen.getByText("○")).toBeInTheDocument();
  });

  it("marks part-time comparisons as made at full-time equivalent", () => {
    render(<BandStatus band={{ ...inBand, compa_ratio: "0.95" }} partTime />);

    expect(screen.getByText("In band · 0.95 FTE")).toBeInTheDocument();
  });

  it("shows a dash when there is no package to compare", () => {
    render(<BandStatus band={null} />);

    expect(screen.getByText("No package")).toBeInTheDocument();
  });
});
