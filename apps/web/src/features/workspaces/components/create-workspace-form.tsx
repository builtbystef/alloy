"use client";

import type { WorkspaceCreate } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createWorkspace } from "@/features/workspaces/mutations";
import { Form, FormError, useAppForm } from "@/components/shared/form";
import { FieldGroup } from "@/components/ui/field";
import { errorMessage } from "@/lib/api/errors";
import { invalidateWorkspaces } from "@/features/workspaces/queries";
import { workspacePaths } from "@/lib/routes";
import { workspaceSchema, type WorkspaceInput } from "@/features/workspaces/schemas";

/** Step one of onboarding; creating the workspace opens step two. */
export function CreateWorkspaceForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (body: WorkspaceCreate) => createWorkspace(body),
    onSuccess: async (workspace) => {
      await invalidateWorkspaces(queryClient);
      router.push(workspacePaths(workspace.id).onboarding);
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
    <Form form={form}>
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="name">
          {(field) => (
            <field.TextField label="Name" placeholder="Acme Sales" autoFocus autoComplete="off" />
          )}
        </form.AppField>
      </FieldGroup>
      <form.AppForm>
        <form.SubmitButton className="self-start">Continue</form.SubmitButton>
      </form.AppForm>
    </Form>
  );
}
