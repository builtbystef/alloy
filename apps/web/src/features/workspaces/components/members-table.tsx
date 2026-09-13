"use client";

import type { MemberRead, WorkspaceRole } from "@alloy/api-client";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { changeMemberRole, removeMember } from "@/features/workspaces/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { browserApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/formatting/dates";
import { roleLabels } from "@/features/workspaces/roles";
import { invalidateWorkspaces, memberListQuery } from "@/features/workspaces/queries";
import { workspaceRoles } from "@/features/workspaces/roles";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

import { assignableRoles, canManageRole } from "@/features/workspaces/roles";

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
      changeMemberRole(workspace.id, member.id, role),
    onSuccess: async (saved) => {
      toast.success(`${saved.email} is now ${roleLabels[saved.role].toLowerCase()}`);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const remove = useMutation({
    mutationFn: async (member: MemberRead) => removeMember(workspace.id, member.id),
    onSuccess: async () => {
      toast.success("Member removed");
      setRemoving(null);
      await invalidateWorkspaces(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const owners = members.filter((m) => m.role === "owner").length;

  return (
    <>
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
      <p className="text-sm text-muted-foreground">
        {members.length} {members.length === 1 ? "person" : "people"}
      </p>
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
    </>
  );
}
