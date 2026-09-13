import { expect, test } from "vite-plus/test";

import { resetPasswordSchema, signupSchema } from "./schemas";

test("signup requires matching passwords", () => {
  const result = signupSchema.safeParse({
    name: "Ada",
    email: "a@b.co",
    password: "longenough",
    confirm: "different",
  });
  expect(result.error?.issues[0]?.path).toEqual(["confirm"]);
});

test("signup requires a name and trims it", () => {
  const valid = { name: "  Ada ", email: "a@b.co", password: "longenough", confirm: "longenough" };
  expect(signupSchema.parse(valid).name).toBe("Ada");
  const blank = signupSchema.safeParse({ ...valid, name: "   " });
  expect(blank.error?.issues.map((issue) => issue.path)).toEqual([["name"]]);
});

test("a reset password form needs matching passwords", () => {
  const result = resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "nope" });
  expect(result.success).toBe(false);
  expect(result.error?.issues.map((issue) => issue.path)).toEqual([["confirm"]]);
  expect(
    resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "long enough" }).success,
  ).toBe(true);
});
