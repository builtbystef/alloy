import { expect, test } from "vite-plus/test";

import {
  companySchema,
  contactSchema,
  parseContactSearch,
  parseTaskSearch,
  resetPasswordSchema,
  signupSchema,
  taskSchema,
  toSearchString,
} from "./schemas";

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

test("company website must be an http(s) URL", () => {
  expect(
    companySchema.safeParse({ name: "Acme", website: "acme", industry: "", notes: "" }).success,
  ).toBe(false);
  expect(
    companySchema.parse({ name: "Acme", website: "https://acme.test", industry: "", notes: "" })
      .website,
  ).toBe("https://acme.test");
});

test("task due date is optional and read in the user's zone", () => {
  const schema = taskSchema("UTC");
  expect(
    schema.parse({
      title: "Call",
      due_at: "",
      status: "open",
      contact_id: "",
      company_id: "",
      notes: "",
    }).due_at,
  ).toBeNull();
  expect(
    schema.safeParse({
      title: "Call",
      due_at: "soon",
      status: "open",
      contact_id: "",
      company_id: "",
      notes: "",
    }).success,
  ).toBe(false);
});

test("signup requires matching passwords", () => {
  const result = signupSchema.safeParse({
    email: "a@b.co",
    password: "longenough",
    confirm: "different",
  });
  expect(result.error?.issues[0]?.path).toEqual(["confirm"]);
});

test("search params keep valid filters and drop the rest", () => {
  expect(parseContactSearch({ q: "ada", status: "bogus", company_id: ["x"] })).toEqual({
    q: "ada",
  });
  expect(parseContactSearch(new URLSearchParams("status=active&q="))).toEqual({ status: "active" });
  expect(parseTaskSearch({ due: "overdue", status: "done" })).toEqual({
    due: "overdue",
    status: "done",
  });
  expect(toSearchString({ q: "ada", status: undefined })).toBe("q=ada");
});

test("search params carry the page and sort of a list", () => {
  expect(parseContactSearch({ page: "3", sort: "company", order: "desc" })).toEqual({
    page: 3,
    sort: "company",
    order: "desc",
  });
  // The first page is the URL without one; anything unknown is dropped.
  expect(parseContactSearch({ page: "1", sort: "email", order: "up" })).toEqual({});
  expect(parseContactSearch({ page: "0" })).toEqual({});
  expect(parseContactSearch({ page: "two" })).toEqual({});
  expect(parseTaskSearch({ sort: "due_at" })).toEqual({ sort: "due_at" });
  expect(toSearchString({ q: "ada", page: 2, sort: undefined })).toBe("q=ada&page=2");
});

test("a reset password form needs matching passwords", () => {
  const result = resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "nope" });
  expect(result.success).toBe(false);
  expect(result.error?.issues.map((issue) => issue.path)).toEqual([["confirm"]]);
  expect(
    resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "long enough" }).success,
  ).toBe(true);
});
