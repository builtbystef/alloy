"use client";

import type { InviteCreate, WorkspaceRole } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { formatDate } from "@/lib/dates";
import { roleDescriptions, roleLabels } from "@/lib/labels";
import { invalidateWorkspaces, inviteListQuery } from "@/lib/queries";
import { inviteSchema, type InviteInput } from "@/lib/schemas";
import { useWorkspace } from "@/lib/workspace";

import { assignableRoles } from "./roles";

export function InvitesCard({ timeZone }: { timeZone: string }) {
  const queryClient = useQueryClient();
  const workspace = useWorkspace();
  const { data: invites } = useSuspenseQuery(inviteListQuery(browserApi, workspace.id));
  const [serverError, setServerError] = useState<string | null>(null);

  const roleOptions = assignableRoles(workspace.role).map((role) => ({
    value: role,
    label: `${roleLabels[role]} · ${roleDescriptions[role]}`,
  }));

  const invite = useMutation({
    mutationFn: async (body: InviteCreate) =>
      unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/invites", {
          params: { path: { workspace_id: workspace.id } },
          body,
        }),
      ),
    onSuccess: async (created) => {
      toast.success(`Invitation sent to ${created.email}`);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) =>
      setServerError(
        error instanceof ApiError && error.status === 409
          ? "That address is already a member or already invited."
          : errorMessage(error),
      ),
  });

  const resend = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/invites/{invite_id}/resend", {
          params: { path: { workspace_id: workspace.id, invite_id: id } },
        }),
      ),
    onSuccess: async (sent) => {
      toast.success(`Invitation sent again to ${sent.email}`);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const revoke = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}/invites/{invite_id}", {
          params: { path: { workspace_id: workspace.id, invite_id: id } },
        }),
      ),
    onSuccess: async () => {
      toast.success("Invitation revoked");
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { email: "", role: "member" as WorkspaceRole } satisfies InviteInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: inviteSchema },
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      await invite.mutateAsync(inviteSchema.parse(value)).then(
        () => formApi.reset(),
        () => {}, // shown through onError
      );
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invite people</CardTitle>
        <CardDescription>
          They get an email with a link that works for seven days, for that address only.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <form
          className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
        >
          <FieldGroup>
            <FormError message={serverError} />
            <div className="grid gap-5 sm:grid-cols-2">
              <form.AppField name="email">
                {(field) => <field.TextField label="Email" type="email" autoComplete="off" />}
              </form.AppField>
              <form.AppField name="role">
                {(field) => <field.SelectField label="Role" options={roleOptions} />}
              </form.AppField>
            </div>
          </FieldGroup>
          <form.AppForm>
            <form.SubmitButton className="self-start">Send invitation</form.SubmitButton>
          </form.AppForm>
        </form>

        {invites.length === 0 ? (
          <p className="text-sm text-muted-foreground">No pending invitations.</p>
        ) : (
          <ul className="divide-y">
            {invites.map((pending) => (
              <li
                key={pending.id}
                className="flex flex-wrap items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{pending.email}</p>
                  <p className="text-sm text-muted-foreground">
                    {roleLabels[pending.role]}
                    {pending.invited_by && ` · invited by ${pending.invited_by}`}
                    {` · expires ${formatDate(pending.expires_at, timeZone)}`}
                  </p>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={resend.isPending}
                    onClick={() => resend.mutate(pending.id)}
                  >
                    Resend
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(pending.id)}
                  >
                    Revoke
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
