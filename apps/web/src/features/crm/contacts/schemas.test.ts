import { expect, test } from "vite-plus/test";

import { contactSchema, parseContactSearch } from "./schemas";

test("contact form values become a request body with empty fields cleared", () => {
  const body = contactSchema("Europe/Belgrade").parse({
    name: "  Ada Lovelace ",
    email: "",
    phone: "",
    job_title: "Engineer",
    company_id: "",
    status: "lead",
    last_contacted_at: "2026-09-07T14:30",
  });
  expect(body).toEqual({
    name: "Ada Lovelace",
    email: null,
    phone: null,
    job_title: "Engineer",
    company_id: null,
    status: "lead",
    last_contacted_at: "2026-09-07T12:30:00.000Z",
  });
});

test("field errors carry the field path", () => {
  const result = contactSchema("UTC").safeParse({
    name: "",
    email: "not-an-email",
    phone: "",
    job_title: "",
    company_id: "",
    status: "lead",
    last_contacted_at: "",
  });
  expect(result.success).toBe(false);
  const paths = result.error?.issues.map((issue) => issue.path.join("."));
  expect(paths).toEqual(["name", "email"]);
});

test("search params keep valid filters and drop the rest", () => {
  expect(parseContactSearch({ q: "ada", status: "bogus", company_id: ["x"] })).toEqual({
    q: "ada",
  });
  expect(parseContactSearch(new URLSearchParams("status=active&q="))).toEqual({ status: "active" });
  expect(parseContactSearch({ page: "3", sort: "company", order: "desc" })).toEqual({
    page: 3,
    sort: "company",
    order: "desc",
  });
  expect(parseContactSearch({ page: "1", sort: "email", order: "up" })).toEqual({});
});
