"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { revalidateLogic } from "@tanstack/react-form";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { FormError, useAppForm } from "@/components/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { authFormSchema, type AuthFormInput } from "@/lib/schemas";

/**
 * Log in and sign up share one component: the same fields, the same API
 * shape, a different endpoint. The API's Set-Cookie comes back through the
 * proxy route, so after success a refresh is enough for Server Components to
 * see the session.
 */
export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const isSignup = mode === "signup";

  const mutation = useMutation({
    mutationFn: async (credentials: { email: string; password: string }) =>
      unwrap(
        isSignup
          ? await browserApi.POST("/auth/signup", { body: credentials })
          : await browserApi.POST("/auth/login", { body: credentials }),
      ),
    onSuccess: () => {
      queryClient.clear();
      const next = searchParams.get("next");
      router.push(next?.startsWith("/") ? (next as "/") : "/");
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
    defaultValues: { email: "", password: "", confirm: "" } as AuthFormInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: authFormSchema(mode) },
    onSubmit: async ({ value }) => {
      setServerError(null);
      // Failures are shown through onError; nothing else to do here.
      await mutation.mutateAsync({ email: value.email, password: value.password }).catch(() => {});
    },
  });

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <Card>
        <CardHeader>
          <CardTitle>{isSignup ? "Create an account" : "Log in"}</CardTitle>
          <CardDescription>
            {isSignup ? "A few seconds and you are in." : "Welcome back to your CRM."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <FormError message={serverError} />
            <form.AppField name="email">
              {(field) => (
                <field.TextField label="Email" type="email" autoComplete="email" autoFocus />
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
                <Link href="/login" className="text-foreground underline underline-offset-4">
                  Log in
                </Link>
              </>
            ) : (
              <>
                New here?{" "}
                <Link href="/signup" className="text-foreground underline underline-offset-4">
                  Create an account
                </Link>
              </>
            )}
          </p>
        </CardFooter>
      </Card>
    </form>
  );
}
