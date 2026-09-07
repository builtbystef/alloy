"use client";

import type { WorkspaceRead, WorkspaceUpdate } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { roleLabels } from "@/lib/labels";
import { invalidateWorkspaces } from "@/lib/queries";
import { workspaceSchema, type WorkspaceInput } from "@/lib/schemas";

export function WorkspaceNameForm({ workspace }: { workspace: WorkspaceRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const canManage = workspace.permissions.includes("workspace:manage");

  const mutation = useMutation({
    mutationFn: async (body: WorkspaceUpdate) =>
      unwrap(
        await browserApi.PATCH("/workspaces/{workspace_id}", {
          params: { path: { workspace_id: workspace.id } },
          body,
        }),
      ),
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
    <Card>
      <CardHeader>
        <CardTitle>General</CardTitle>
        <CardDescription>
          You are {roleLabels[workspace.role].toLowerCase()} of this workspace.
          {!canManage && " Only admins and owners can rename it."}
        </CardDescription>
      </CardHeader>
      <CardContent>
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
              {(field) => <field.TextField label="Name" disabled={!canManage} />}
            </form.AppField>
          </FieldGroup>
          {canManage && (
            <form.AppForm>
              <form.SubmitButton className="self-start">Save</form.SubmitButton>
            </form.AppForm>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
