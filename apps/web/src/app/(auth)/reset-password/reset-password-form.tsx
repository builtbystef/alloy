"use client";

import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { resetPasswordSchema, type ResetPasswordInput } from "@/lib/schemas";

/** Choose a new password. Success logs in on this browser and goes to the app. */
export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const [linkDead, setLinkDead] = useState(false);

  const mutation = useMutation({
    mutationFn: async (newPassword: string) =>
      unwrap(
        await browserApi.POST("/auth/reset-password", {
          body: { token, new_password: newPassword },
        }),
      ),
    onSuccess: () => {
      queryClient.clear();
      router.push("/");
      router.refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        setLinkDead(true);
        setServerError("This link was already used or never existed.");
      } else if (error instanceof ApiError && error.status === 410) {
        setLinkDead(true);
        setServerError("This link has expired.");
      } else {
        setServerError(errorMessage(error));
      }
    },
  });

  const form = useAppForm({
    defaultValues: { new_password: "", confirm: "" } satisfies ResetPasswordInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: resetPasswordSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      // Failures are shown through onError.
      await mutation.mutateAsync(value.new_password).catch(() => {});
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
          <CardTitle>Choose a new password</CardTitle>
          <CardDescription>
            You will be logged in here, and logged out everywhere else.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <FormError message={serverError} />
            <form.AppField name="new_password">
              {(field) => (
                <field.TextField
                  label="New password"
                  type="password"
                  autoComplete="new-password"
                  description="At least 8 characters."
                  autoFocus
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
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <form.AppForm>
            <form.SubmitButton disabled={linkDead || mutation.isSuccess}>
              Set new password
            </form.SubmitButton>
          </form.AppForm>
          {linkDead && (
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href="/forgot-password" />}
            >
              Request a new link
            </Button>
          )}
        </CardFooter>
      </Card>
    </form>
  );
}
