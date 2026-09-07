"use client";

import type { MemberRead, WorkspaceRole } from "@alloy/api-client";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { formatDate } from "@/lib/dates";
import { roleLabels } from "@/lib/labels";
import { invalidateWorkspaces, memberListQuery } from "@/lib/queries";
import { workspaceRoles } from "@/lib/schemas";
import { useCan, useWorkspace } from "@/lib/workspace";

import { assignableRoles, canManageRole } from "./roles";

export function MembersTable({
  timeZone,
  currentEmail,
}: {
  timeZone: string;
  currentEmail: string;
}) {
  const queryClient = useQueryClient();
  const workspace = useWorkspace();
  const canManage = useCan("members:manage");
  const { data: members } = useSuspenseQuery(memberListQuery(browserApi, workspace.id));
  const [removing, setRemoving] = useState<MemberRead | null>(null);

  const changeRole = useMutation({
    mutationFn: async ({ member, role }: { member: MemberRead; role: WorkspaceRole }) =>
      unwrap(
        await browserApi.PATCH("/workspaces/{workspace_id}/members/{member_id}", {
          params: { path: { workspace_id: workspace.id, member_id: member.id } },
          body: { role },
        }),
      ),
    onSuccess: async (saved) => {
      toast.success(`${saved.email} is now ${roleLabels[saved.role].toLowerCase()}`);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const remove = useMutation({
    mutationFn: async (member: MemberRead) =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}/members/{member_id}", {
          params: { path: { workspace_id: workspace.id, member_id: member.id } },
        }),
      ),
    onSuccess: async () => {
      toast.success("Member removed");
      setRemoving(null);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const owners = members.filter((m) => m.role === "owner").length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Members</CardTitle>
        <CardDescription>
          {members.length} {members.length === 1 ? "person" : "people"}. Owners can do everything;
          admins manage members and settings; members edit records; viewers only read.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
                {canManage && <TableHead className="w-24" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member) => {
                const isSelf = member.email === currentEmail;
                const editable =
                  canManage &&
                  !isSelf &&
                  canManageRole(workspace.role, member.role) &&
                  !(member.role === "owner" && owners <= 1);
                return (
                  <TableRow key={member.id}>
                    <TableCell className="font-medium">
                      {member.email}
                      {isSelf && (
                        <Badge variant="outline" className="ml-2">
                          You
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {editable ? (
                        <NativeSelect
                          value={member.role}
                          disabled={changeRole.isPending}
                          onChange={(event) =>
                            changeRole.mutate({
                              member,
                              role: event.target.value as WorkspaceRole,
                            })
                          }
                          aria-label={`Role of ${member.email}`}
                        >
                          {workspaceRoles.map((role) => (
                            <NativeSelectOption
                              key={role}
                              value={role}
                              disabled={!assignableRoles(workspace.role).includes(role)}
                            >
                              {roleLabels[role]}
                            </NativeSelectOption>
                          ))}
                        </NativeSelect>
                      ) : (
                        roleLabels[member.role]
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(member.created_at, timeZone)}
                    </TableCell>
                    {canManage && (
                      <TableCell className="text-right">
                        {editable && (
                          <Button variant="ghost" size="sm" onClick={() => setRemoving(member)}>
                            Remove
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => {
          if (!open) setRemoving(null);
        }}
        title={`Remove ${removing?.email ?? "this member"}?`}
        description="They lose access to this workspace at once. Records they created stay."
        confirmLabel="Remove"
        pending={remove.isPending}
        onConfirm={() => removing && remove.mutate(removing)}
      />
    </Card>
  );
}
