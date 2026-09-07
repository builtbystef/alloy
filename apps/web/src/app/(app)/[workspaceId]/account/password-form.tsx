"use client";

import type { PasswordChange } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { passwordChangeSchema, type PasswordChangeInput } from "@/lib/schemas";

export function PasswordForm({ email }: { email: string }) {
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (body: PasswordChange) =>
      unwrap(await browserApi.POST("/auth/password", { body })),
    onSuccess: () => toast.success("Password changed. Other devices were logged out."),
    onError: (error) =>
      setServerError(
        error instanceof ApiError && error.status === 401
          ? "The current password is incorrect."
          : errorMessage(error),
      ),
  });

  const form = useAppForm({
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm: "",
    } satisfies PasswordChangeInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: passwordChangeSchema },
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      await mutation
        .mutateAsync({ current_password: value.current_password, new_password: value.new_password })
        .then(
          () => formApi.reset(),
          () => {}, // shown through onError
        );
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
        <CardDescription>Signed in as {email}.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="flex flex-col gap-6"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
        >
          {/* Lets password managers associate the new password with the account. */}
          <input type="hidden" name="username" value={email} autoComplete="username" />
          <FieldGroup>
            <FormError message={serverError} />
            <form.AppField name="current_password">
              {(field) => (
                <field.TextField
                  label="Current password"
                  type="password"
                  autoComplete="current-password"
                />
              )}
            </form.AppField>
            <form.AppField name="new_password">
              {(field) => (
                <field.TextField
                  label="New password"
                  type="password"
                  autoComplete="new-password"
                  description="At least 8 characters."
                />
              )}
            </form.AppField>
            <form.AppField name="confirm">
              {(field) => (
                <field.TextField
                  label="Confirm new password"
                  type="password"
                  autoComplete="new-password"
                />
              )}
            </form.AppField>
          </FieldGroup>
          <form.AppForm>
            <form.SubmitButton className="self-start">Change password</form.SubmitButton>
          </form.AppForm>
        </form>
      </CardContent>
    </Card>
  );
}
