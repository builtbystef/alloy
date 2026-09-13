"use client";

import type { EmailChangeRequest } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { cancelEmailChange, requestEmailChange } from "@/features/auth/mutations";
import { Form, FormError, useAppForm } from "@/components/shared/form";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { emailChangeSchema, type EmailChangeInput } from "@/features/auth/schemas";

/** `pendingEmail` comes from the server render, so `router.refresh()` updates it. */
export function EmailForm({ pendingEmail }: { pendingEmail: string | null }) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const request = useMutation({
    mutationFn: async (body: EmailChangeRequest) => requestEmailChange(body),
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
    mutationFn: cancelEmailChange,
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
    <>
      {pendingEmail !== null && (
        <Alert>
          <AlertTitle>Waiting for confirmation</AlertTitle>
          <AlertDescription className="gap-3">
            <p>
              We sent a link to <strong>{pendingEmail}</strong>. Follow it within a day to move your
              account there. Submitting a new address sends a new link.
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
      <Form form={form}>
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
      </Form>
    </>
  );
}
