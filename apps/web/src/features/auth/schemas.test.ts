import { expect, test } from "vite-plus/test";

import { resetPasswordSchema, signupSchema } from "./schemas";

test("signup requires matching passwords", () => {
  const result = signupSchema.safeParse({
    email: "a@b.co",
    password: "longenough",
    confirm: "different",
  });
  expect(result.error?.issues[0]?.path).toEqual(["confirm"]);
});

test("a reset password form needs matching passwords", () => {
  const result = resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "nope" });
  expect(result.success).toBe(false);
  expect(result.error?.issues.map((issue) => issue.path)).toEqual([["confirm"]]);
  expect(
    resetPasswordSchema.safeParse({ new_password: "long enough", confirm: "long enough" }).success,
  ).toBe(true);
});
