"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { revalidateLogic } from "@tanstack/react-form";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { Signup } from "@alloy/api-client";
import { login, signup } from "@/features/auth/mutations";
import { Form, FormError, useAppForm } from "@/components/shared/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { safeNextPath } from "@/lib/routes";
import { authFormSchema, type AuthFormInput } from "@/features/auth/schemas";

/**
 * Log in and sign up share one component: the same fields, the same API
 * shape, a different endpoint. The API's Set-Cookie comes back through the
 * proxy route, so after success a refresh is enough for Server Components to
 * see the session.
 *
 * A new account goes to /verify-email, unless it came from an invitation:
 * accepting one verifies the address, so the invite page is the shorter path.
 * Only the invited address can accept, so sign-up fills it in, keeps it, and
 * sends the token so the API skips the verification email.
 */
export function AuthForm({
  mode,
  invite = null,
}: {
  mode: "login" | "signup";
  invite?: { token: string; email: string } | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const isSignup = mode === "signup";
  // Kept across the login/sign-up links, so an invitation survives either path.
  const next = searchParams.get("next");
  const search = next ? `?next=${encodeURIComponent(next)}` : "";
  const isInvite = invite !== null;
  const destination = safeNextPath(next) as "/";

  const mutation = useMutation({
    mutationFn: (body: Signup) => (isSignup ? signup(body) : login(body)),
    onSuccess: () => {
      queryClient.clear();
      if (isSignup && !isInvite) {
        router.push("/verify-email");
      } else {
        router.push(destination);
      }
      router.refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        setServerError("That email and password do not match.");
      } else if (error instanceof ApiError && error.status === 409) {
        setServerError("An account with this email already exists.");
      } else {
        setServerError(errorMessage(error));
      }
    },
  });

  const form = useAppForm({
    defaultValues: {
      name: "",
      email: invite?.email ?? "",
      password: "",
      confirm: "",
    } as AuthFormInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: authFormSchema(mode) },
    onSubmit: async ({ value }) => {
      setServerError(null);
      // Failures are shown through onError.
      await mutation
        .mutateAsync({
          name: value.name.trim(),
          email: value.email,
          password: value.password,
          ...(isSignup && invite ? { invite_token: invite.token } : {}),
        })
        .catch(() => {});
    },
  });

  return (
    <Form form={form}>
      <Card>
        <CardHeader>
          <CardTitle>{isSignup ? "Create an account" : "Log in"}</CardTitle>
          <CardDescription>
            {isInvite
              ? `${isSignup ? "Create an account" : "Log in"} to accept your invitation.`
              : isSignup
                ? "A few seconds and you are in."
                : "Welcome back to your CRM."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <FormError message={serverError} />
            {isSignup && (
              <form.AppField name="name">
                {(field) => <field.TextField label="Name" autoComplete="name" autoFocus />}
              </form.AppField>
            )}
            <form.AppField name="email">
              {(field) => (
                <field.TextField
                  label="Email"
                  type="email"
                  autoComplete="email"
                  autoFocus={!isSignup}
                  readOnly={isSignup && isInvite}
                  {...(isSignup && isInvite
                    ? { description: "The invitation is for this address." }
                    : {})}
                />
              )}
            </form.AppField>
            <form.AppField name="password">
              {(field) => (
                <field.TextField
                  label="Password"
                  type="password"
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  {...(isSignup ? { description: "At least 8 characters." } : {})}
                />
              )}
            </form.AppField>
            {!isSignup && (
              <p className="-mt-2 text-sm">
                <Link
                  href="/forgot-password"
                  className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
                >
                  Forgot your password?
                </Link>
              </p>
            )}
            {isSignup && (
              <form.AppField name="confirm">
                {(field) => (
                  <field.TextField
                    label="Confirm password"
                    type="password"
                    autoComplete="new-password"
                  />
                )}
              </form.AppField>
            )}
          </FieldGroup>
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <form.AppForm>
            <form.SubmitButton>{isSignup ? "Sign up" : "Log in"}</form.SubmitButton>
          </form.AppForm>
          <p className="text-center text-sm text-muted-foreground">
            {isSignup ? (
              <>
                Already have an account?{" "}
                <Link
                  href={`/login${search}`}
                  className="text-foreground underline underline-offset-4"
                >
                  Log in
                </Link>
              </>
            ) : (
              <>
                New here?{" "}
                <Link
                  href={`/signup${search}`}
                  className="text-foreground underline underline-offset-4"
                >
                  Create an account
                </Link>
              </>
            )}
          </p>
        </CardFooter>
      </Card>
    </Form>
  );
}
