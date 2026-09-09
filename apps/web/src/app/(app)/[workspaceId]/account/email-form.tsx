"use client";

import type { EmailChangeRequest } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { emailChangeSchema, type EmailChangeInput } from "@/lib/schemas";

/** `pendingEmail` comes from the server render, so `router.refresh()` updates it. */
export function EmailForm({ email, pendingEmail }: { email: string; pendingEmail: string | null }) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const request = useMutation({
    mutationFn: async (body: EmailChangeRequest) =>
      unwrap(await browserApi.POST("/auth/change-email", { body })),
    onSuccess: (_, body) => {
      toast.success(`Check ${body.new_email} for a link to confirm the change.`);
      router.refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        setServerError("The password is incorrect.");
      } else if (error instanceof ApiError && error.status === 409) {
        setServerError("That address is already in use.");
      } else {
        setServerError(errorMessage(error));
      }
    },
  });

  const cancel = useMutation({
    mutationFn: async () => unwrap(await browserApi.DELETE("/auth/change-email")),
    onSuccess: () => {
      toast.success("Email change cancelled.");
      router.refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { new_email: "", current_password: "" } satisfies EmailChangeInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: emailChangeSchema },
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      await request.mutateAsync(value).then(
        () => formApi.reset(),
        () => {}, // shown through onError
      );
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Email</CardTitle>
        <CardDescription>
          Your login is <strong>{email}</strong>. A new address takes effect once you follow the
          link we send to it.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {pendingEmail !== null && (
          <Alert>
            <AlertTitle>Waiting for confirmation</AlertTitle>
            <AlertDescription className="gap-3">
              <p>
                We sent a link to <strong>{pendingEmail}</strong>. Follow it within a day to move
                your account there. Submitting a new address sends a new link.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="self-start"
                onClick={() => cancel.mutate()}
                disabled={cancel.isPending}
              >
                Cancel change
              </Button>
            </AlertDescription>
          </Alert>
        )}
        <form
          className="flex flex-col gap-6"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
        >
          <FieldGroup>
            <FormError message={serverError} />
            <form.AppField name="new_email">
              {(field) => <field.TextField label="New email" type="email" autoComplete="email" />}
            </form.AppField>
            <form.AppField name="current_password">
              {(field) => (
                <field.TextField
                  label="Current password"
                  type="password"
                  autoComplete="current-password"
                  description="To confirm it is you."
                />
              )}
            </form.AppField>
          </FieldGroup>
          <form.AppForm>
            <form.SubmitButton className="self-start">Send confirmation link</form.SubmitButton>
          </form.AppForm>
        </form>
      </CardContent>
    </Card>
  );
}
