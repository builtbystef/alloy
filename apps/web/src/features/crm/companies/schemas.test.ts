import { expect, test } from "vite-plus/test";

import { companySchema, parseCompanySearch } from "./schemas";

test("company website must be an http(s) URL", () => {
  expect(
    companySchema.safeParse({ name: "Acme", website: "acme", industry: "", notes: "" }).success,
  ).toBe(false);
  expect(
    companySchema.parse({ name: "Acme", website: "https://acme.test", industry: "", notes: "" })
      .website,
  ).toBe("https://acme.test");
});

test("company search keeps its own sorts only", () => {
  expect(parseCompanySearch({ q: "acme", sort: "industry", order: "asc" })).toEqual({
    q: "acme",
    sort: "industry",
    order: "asc",
  });
  expect(parseCompanySearch({ sort: "status" })).toEqual({});
});
