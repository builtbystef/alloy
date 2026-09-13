import { expect, test } from "vite-plus/test";

import { parseTaskSearch, taskSchema } from "./schemas";

const input = { title: "Call", due_at: "", status: "open", related: "", notes: "" } as const;

test("task due date is optional and read in the user's zone", () => {
  const schema = taskSchema("UTC");
  expect(schema.parse(input).due_at).toBeNull();
  expect(schema.safeParse({ ...input, due_at: "soon" }).success).toBe(false);
});

test("the related-to picker's value becomes one of the two link ids", () => {
  const schema = taskSchema("UTC");
  const id = "0192a1b2-0000-7000-8000-000000000001";
  expect(schema.parse(input)).toMatchObject({ contact_id: null, company_id: null });
  expect(schema.parse({ ...input, related: `contact:${id}` })).toMatchObject({
    contact_id: id,
    company_id: null,
  });
  expect(schema.parse({ ...input, related: `company:${id}` })).toMatchObject({
    contact_id: null,
    company_id: id,
  });
  expect(schema.safeParse({ ...input, related: id }).success).toBe(false);
  expect(schema.safeParse({ ...input, related: "contact:nope" }).success).toBe(false);
});

test("task search keeps valid filters and drops the rest", () => {
  expect(parseTaskSearch({ due: "overdue", status: "done" })).toEqual({
    due: "overdue",
    status: "done",
  });
  expect(parseTaskSearch({ sort: "due_at", due: "never" })).toEqual({ sort: "due_at" });
});
