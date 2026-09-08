"use client";

import { revalidateLogic } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { MailIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { FormError, useAppForm } from "@/components/form";
import { Button } from "@/components/ui/button";
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
import { errorMessage, unwrap } from "@/lib/api-error";
import { forgotPasswordSchema, type ForgotPasswordInput } from "@/lib/schemas";

/**
 * Asks for the address and reports success either way: the API answers 204
 * whether or not an account exists, so this page cannot tell and does not try.
 */
export function ForgotPasswordForm() {
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (email: string) =>
      unwrap(await browserApi.POST("/auth/forgot-password", { body: { email } })),
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { email: "" } satisfies ForgotPasswordInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: forgotPasswordSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      // Failures are shown through onError.
      await mutation.mutateAsync(value.email).catch(() => {});
    },
  });

  if (mutation.isSuccess) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MailIcon className="size-5" /> Check your inbox
          </CardTitle>
          <CardDescription>
            If an account exists for <strong>{mutation.variables}</strong>, a link to choose a new
            password is on its way. It works for one hour.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Nothing there? Check your spam folder, or make sure you used the address you signed up
            with.
          </p>
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <Button variant="outline" onClick={() => mutation.reset()}>
            Try another email
          </Button>
          <Button variant="ghost" nativeButton={false} render={<Link href="/login" />}>
            Back to log in
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <Card>
        <CardHeader>
          <CardTitle>Forgot your password?</CardTitle>
          <CardDescription>
            Enter your email and we will send you a link to choose a new one.
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
          </FieldGroup>
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <form.AppForm>
            <form.SubmitButton>Send reset link</form.SubmitButton>
          </form.AppForm>
          <p className="text-center text-sm text-muted-foreground">
            Remembered it?{" "}
            <Link href="/login" className="text-foreground underline underline-offset-4">
              Log in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </form>
  );
}
