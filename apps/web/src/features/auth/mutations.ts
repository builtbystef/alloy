import type {
  AccountDeletion,
  Credentials,
  EmailChangeRequest,
  PasswordChange,
  UserRead,
} from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function login(credentials: Credentials): Promise<UserRead> {
  return unwrap(await browserApi.POST("/auth/login", { body: credentials }));
}

/** Also creates the account's first workspace. */
export async function signup(credentials: Credentials): Promise<UserRead> {
  return unwrap(await browserApi.POST("/auth/signup", { body: credentials }));
}

export async function logout(): Promise<void> {
  unwrap(await browserApi.POST("/auth/logout"));
}

/** Every session, this one included. */
export async function logoutAll(): Promise<void> {
  unwrap(await browserApi.POST("/auth/logout-all"));
}

export async function verifyEmail(token: string): Promise<UserRead> {
  return unwrap(await browserApi.POST("/auth/verify-email", { body: { token } }));
}

export async function resendVerification(): Promise<void> {
  unwrap(await browserApi.POST("/auth/resend-verification"));
}

export async function forgotPassword(email: string): Promise<void> {
  unwrap(await browserApi.POST("/auth/forgot-password", { body: { email } }));
}

export async function resetPassword(token: string, newPassword: string): Promise<UserRead> {
  return unwrap(
    await browserApi.POST("/auth/reset-password", { body: { token, new_password: newPassword } }),
  );
}

export async function changePassword(body: PasswordChange): Promise<void> {
  unwrap(await browserApi.POST("/auth/password", { body }));
}

export async function requestEmailChange(body: EmailChangeRequest): Promise<void> {
  unwrap(await browserApi.POST("/auth/change-email", { body }));
}

export async function cancelEmailChange(): Promise<void> {
  unwrap(await browserApi.DELETE("/auth/change-email"));
}

export async function confirmEmailChange(token: string): Promise<UserRead> {
  return unwrap(await browserApi.POST("/auth/confirm-email", { body: { token } }));
}

export async function deleteAccount(body: AccountDeletion): Promise<void> {
  unwrap(await browserApi.POST("/auth/delete-account", { body }));
}
