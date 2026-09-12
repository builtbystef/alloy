import { expect, test } from "vite-plus/test";

import { parseTaskSearch, taskSchema } from "./schemas";

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

test("task search keeps valid filters and drops the rest", () => {
  expect(parseTaskSearch({ due: "overdue", status: "done" })).toEqual({
    due: "overdue",
    status: "done",
  });
  expect(parseTaskSearch({ sort: "due_at", due: "never" })).toEqual({ sort: "due_at" });
});
