import { describe, expect, it } from "vitest";

import { DEFAULT_FILTERS, filtersFromParams, filtersToParams, toApiParams } from "./filters";

describe("directory filters in the URL", () => {
  it("reads filters, sort and page from search params", () => {
    const params = new URLSearchParams(
      "q=Ravi&country=IN&department=1&band=below&type=part_time&sort=total_pay_usd&order=desc&page=3",
    );

    expect(filtersFromParams(params)).toEqual({
      ...DEFAULT_FILTERS,
      q: "Ravi",
      country: "IN",
      department: "1",
      band: "below",
      type: "part_time",
      sort: "total_pay_usd",
      order: "desc",
      page: 3,
    });
  });

  it("round-trips through the URL", () => {
    const filters = { ...DEFAULT_FILTERS, country: "DE", level: "4", status: "terminated", page: 2 };

    expect(filtersFromParams(filtersToParams(filters))).toEqual(filters);
  });

  it("keeps the URL short by leaving defaults out", () => {
    expect(filtersToParams(DEFAULT_FILTERS).toString()).toBe("");
    expect(filtersToParams({ ...DEFAULT_FILTERS, country: "IN" }).toString()).toBe("country=IN");
  });

  it("ignores values it doesn't recognise instead of failing", () => {
    const filters = filtersFromParams(new URLSearchParams("band=sideways&sort=shoe&page=-4"));

    expect(filters).toEqual(DEFAULT_FILTERS);
  });

  it("maps URL filters to the API's query parameters", () => {
    const filters = { ...DEFAULT_FILTERS, band: "below", type: "contractor", page: 2 };

    expect(toApiParams(filters).toString()).toBe(
      "band_position=below&employment_type=contractor&sort=name&order=asc&page=2&page_size=25",
    );
  });

  it("asks for current employees unless a status is chosen", () => {
    expect(toApiParams(DEFAULT_FILTERS).getAll("status")).toEqual([]);
    expect(toApiParams({ ...DEFAULT_FILTERS, status: "terminated" }).getAll("status")).toEqual([
      "terminated",
    ]);
  });
});
