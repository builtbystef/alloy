"use client";

import type { AccountDeletion } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { accountDeletionSchema, type AccountDeletionInput } from "@/lib/schemas";
import { WORKSPACE_COOKIE } from "@/lib/workspace-shared";

export function DeleteAccountCard() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const remove = useMutation({
    mutationFn: async (body: AccountDeletion) =>
      unwrap(await browserApi.POST("/auth/delete-account", { body })),
    onSuccess: () => {
      toast.success("Your account is scheduled for deletion. Log in within 7 days to keep it.");
      document.cookie = `${WORKSPACE_COOKIE}=; Path=/; Max-Age=0`;
      queryClient.clear();
      router.push("/login");
      router.refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        setServerError("The password is incorrect.");
      } else {
        // A 409 names the workspaces that need another owner first.
        setServerError(errorMessage(error));
      }
    },
  });

  const form = useAppForm({
    defaultValues: { current_password: "" } satisfies AccountDeletionInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: accountDeletionSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await remove.mutateAsync(value).catch(() => {}); // shown through onError
    },
  });

  const onOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      setServerError(null);
      form.reset();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Delete account</CardTitle>
        <CardDescription>
          Logs you out everywhere and removes the account after 7 days, along with every workspace
          you are the only member of. Logging in before then cancels it.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-2">
        <Button variant="destructive" onClick={() => onOpenChange(true)}>
          Delete account
        </Button>
        <p className="text-sm text-muted-foreground">
          Workspaces you share must have another owner first.
        </p>
      </CardContent>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent showCloseButton={false}>
          <form
            className="flex flex-col gap-6"
            onSubmit={(event) => {
              event.preventDefault();
              void form.handleSubmit();
            }}
          >
            <DialogHeader>
              <DialogTitle>Delete your account?</DialogTitle>
              <DialogDescription>
                You will be logged out everywhere. Your account and any workspace you are alone in
                are removed for good after 7 days, unless you log in again.
              </DialogDescription>
            </DialogHeader>
            <FieldGroup>
              <FormError message={serverError} />
              <form.AppField name="current_password">
                {(field) => (
                  <field.TextField
                    label="Your password"
                    type="password"
                    autoComplete="current-password"
                  />
                )}
              </form.AppField>
            </FieldGroup>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />} disabled={remove.isPending}>
                Cancel
              </DialogClose>
              <form.Subscribe selector={(state) => state.isSubmitting}>
                {(isSubmitting) => (
                  <Button type="submit" variant="destructive" disabled={isSubmitting}>
                    Delete my account
                  </Button>
                )}
              </form.Subscribe>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
