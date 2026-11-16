import { describe, expect, it } from "vitest";

import {
  DEFAULT_INSIGHT_FILTERS,
  activeGroup,
  directoryHref,
  groupOptions,
  insightApiParams,
  insightFiltersFromParams,
  insightFiltersToParams,
} from "./insight-filters";

describe("insight filters in the URL", () => {
  it("reads filters, grouping and currency from search params", () => {
    const params = new URLSearchParams("country=IN&department=2&level=3&type=part_time&group=level&currency=usd");

    expect(insightFiltersFromParams(params)).toEqual({
      country: "IN",
      department: "2",
      level: "3",
      type: "part_time",
      group: "level",
      currency: "usd",
    });
  });

  it("drops unknown values rather than sending them to the API", () => {
    const params = new URLSearchParams("country=india&level=9&type=intern&group=role&currency=eur");

    expect(insightFiltersFromParams(params)).toEqual(DEFAULT_INSIGHT_FILTERS);
  });

  it("round-trips through the URL, leaving defaults out", () => {
    const filters = { ...DEFAULT_INSIGHT_FILTERS, country: "DE", group: "department" as const, currency: "usd" as const };

    expect(insightFiltersToParams(filters).toString()).toBe("country=DE&group=department&currency=usd");
    expect(insightFiltersFromParams(insightFiltersToParams(filters))).toEqual(filters);
    expect(insightFiltersToParams(DEFAULT_INSIGHT_FILTERS).toString()).toBe("");
  });
});

describe("grouping within a selection", () => {
  it("offers every grouping when nothing is filtered", () => {
    expect(groupOptions(DEFAULT_INSIGHT_FILTERS).map((g) => g.key)).toEqual(["country", "department", "level"]);
  });

  it("leaves out the dimensions already narrowed to one value", () => {
    const filters = { ...DEFAULT_INSIGHT_FILTERS, country: "IN", level: "4" };

    expect(groupOptions(filters).map((g) => g.key)).toEqual(["department"]);
  });

  it("falls back to the first available grouping", () => {
    const filters = { ...DEFAULT_INSIGHT_FILTERS, country: "IN", group: "country" as const };

    expect(activeGroup(filters)).toBe("department");
    expect(activeGroup({ ...filters, department: "1", level: "2" })).toBeNull();
  });
});

describe("insight API parameters", () => {
  it("asks for local currency only when one country is selected", () => {
    expect(insightApiParams({ ...DEFAULT_INSIGHT_FILTERS, country: "IN" }).toString()).toBe(
      "country=IN&currency=local",
    );
    expect(insightApiParams({ ...DEFAULT_INSIGHT_FILTERS, country: "IN", currency: "usd" }).toString()).toBe(
      "country=IN&currency=usd",
    );
    expect(insightApiParams(DEFAULT_INSIGHT_FILTERS).toString()).toBe("currency=usd");
  });

  it("sends the employment type under the API's name", () => {
    const params = insightApiParams({ ...DEFAULT_INSIGHT_FILTERS, department: "3", level: "2", type: "contractor" });

    expect(params.toString()).toBe("department=3&level=2&employment_type=contractor&currency=usd");
  });
});

describe("link to the people behind the numbers", () => {
  it("opens the directory with the same filters", () => {
    const filters = { ...DEFAULT_INSIGHT_FILTERS, country: "IN", type: "full_time", group: "level" as const };

    expect(directoryHref(filters)).toBe("/employees?country=IN&type=full_time");
    expect(directoryHref(DEFAULT_INSIGHT_FILTERS)).toBe("/employees");
  });
});
