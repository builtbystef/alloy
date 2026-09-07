"use client";

import type { WorkspaceCreate } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { invalidateWorkspaces } from "@/lib/queries";
import { workspaceSchema, type WorkspaceInput } from "@/lib/schemas";

/** Creates a workspace and opens it. Used on first sign-up and from the switcher. */
export function CreateWorkspaceForm({ onCreated }: { onCreated?: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (body: WorkspaceCreate) =>
      unwrap(await browserApi.POST("/workspaces/", { body })),
    onSuccess: async (workspace) => {
      toast.success(`Workspace "${workspace.name}" created`);
      await invalidateWorkspaces(queryClient);
      onCreated?.();
      router.push(`/${workspace.id}`);
      router.refresh();
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { name: "" } satisfies WorkspaceInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: workspaceSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(workspaceSchema.parse(value)).catch(() => {});
    },
  });

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="name">
          {(field) => (
            <field.TextField label="Name" placeholder="Acme Sales" autoFocus autoComplete="off" />
          )}
        </form.AppField>
      </FieldGroup>
      <form.AppForm>
        <form.SubmitButton className="self-start">Create workspace</form.SubmitButton>
      </form.AppForm>
    </form>
  );
}

export function WorkspaceDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New workspace</DialogTitle>
          <DialogDescription>
            A separate set of contacts, companies, and tasks, with its own members. You will be its
            owner.
          </DialogDescription>
        </DialogHeader>
        {open && <CreateWorkspaceForm onCreated={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  );
}
