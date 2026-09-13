import { z } from "zod";

import { requiredText } from "@/lib/validation";

const password = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(128, "Password must be at most 128 characters");

export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export const signupSchema = z
  .object({
    name: requiredText("Name", 100),
    email: z.email("Enter a valid email address"),
    password,
    confirm: z.string(),
  })
  .refine((value) => value.password === value.confirm, {
    error: "Passwords do not match",
    path: ["confirm"],
  });

/** One input shape for the shared auth form; only sign-up checks `name` and `confirm`. */
export const authFormSchema = (mode: "login" | "signup") =>
  mode === "signup" ? signupSchema : loginSchema.extend({ name: z.string(), confirm: z.string() });

export const forgotPasswordSchema = z.object({
  email: z.email("Enter a valid email address"),
});

export const resetPasswordSchema = z
  .object({
    new_password: password,
    confirm: z.string(),
  })
  .refine((value) => value.new_password === value.confirm, {
    error: "Passwords do not match",
    path: ["confirm"],
  });

export const passwordChangeSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: password,
    confirm: z.string(),
  })
  .refine((value) => value.new_password === value.confirm, {
    error: "Passwords do not match",
    path: ["confirm"],
  });

export const profileSchema = z.object({
  name: requiredText("Name", 100),
});

export const emailChangeSchema = z.object({
  new_email: z.email("Enter a valid email address"),
  current_password: z.string().min(1, "Your password is required"),
});

export const accountDeletionSchema = z.object({
  current_password: z.string().min(1, "Your password is required"),
});

export type LoginInput = z.input<typeof loginSchema>;
export type SignupInput = z.input<typeof signupSchema>;
export type AuthFormInput = z.input<ReturnType<typeof authFormSchema>>;
export type ForgotPasswordInput = z.input<typeof forgotPasswordSchema>;
export type ResetPasswordInput = z.input<typeof resetPasswordSchema>;
export type PasswordChangeInput = z.input<typeof passwordChangeSchema>;
export type ProfileInput = z.input<typeof profileSchema>;
export type EmailChangeInput = z.input<typeof emailChangeSchema>;
export type AccountDeletionInput = z.input<typeof accountDeletionSchema>;
