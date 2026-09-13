"use client";

import type { WorkspaceRead, WorkspaceUpdate } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { updateWorkspace } from "@/features/workspaces/mutations";
import { Form, FormError, useAppForm } from "@/components/shared/form";
import { FieldGroup } from "@/components/ui/field";
import { errorMessage } from "@/lib/api/errors";
import { invalidateWorkspaces } from "@/features/workspaces/queries";
import { workspaceSchema, type WorkspaceInput } from "@/features/workspaces/schemas";

export function WorkspaceNameForm({ workspace }: { workspace: WorkspaceRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const canManage = workspace.permissions.includes("workspace:manage");

  const mutation = useMutation({
    mutationFn: async (body: WorkspaceUpdate) => updateWorkspace(workspace.id, body),
    onSuccess: async () => {
      toast.success("Workspace renamed");
      await invalidateWorkspaces(queryClient);
      // The name is rendered by Server Components (sidebar), so refresh them.
      router.refresh();
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { name: workspace.name } satisfies WorkspaceInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: workspaceSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(workspaceSchema.parse(value)).catch(() => {});
    },
  });

  return (
    <Form form={form}>
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="name">
          {(field) => <field.TextField label="Name" disabled={!canManage} />}
        </form.AppField>
      </FieldGroup>
      {canManage && (
        <form.AppForm>
          <form.SubmitButton className="self-start" requireChanges>
            Save
          </form.SubmitButton>
        </form.AppForm>
      )}
    </Form>
  );
}
