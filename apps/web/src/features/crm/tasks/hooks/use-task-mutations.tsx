"use client";

import type { TaskRead, TaskStatus } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { deleteTask, updateTask } from "@/features/crm/tasks/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { errorMessage } from "@/lib/api/errors";
import { invalidateCrm } from "@/features/crm/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

import { TaskDialog } from "@/features/crm/tasks/components/task-dialog";

/**
 * Everything a task row can do: toggle done, edit in a dialog, delete after
 * confirming. Render `dialogs` once near the list.
 */
export function useTaskMutations({
  timeZone,
  defaults,
}: {
  timeZone: string;
  defaults?: { contact_id?: string; company_id?: string };
}): {
  setStatus: (task: TaskRead, status: TaskStatus) => void;
  pendingStatusId: string | null;
  openCreate: () => void;
  openEdit: (task: TaskRead) => void;
  confirmDelete: (task: TaskRead) => void;
  dialogs: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [editing, setEditing] = useState<TaskRead | "new" | null>(null);
  const [deleting, setDeleting] = useState<TaskRead | null>(null);

  const status = useMutation({
    mutationFn: async ({ task, status }: { task: TaskRead; status: TaskStatus }) =>
      updateTask(workspaceId, task.id, { status }),
    onSuccess: async (saved) => {
      if (saved.status === "done") toast.success("Task completed");
      await invalidateCrm(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteTask(workspaceId, id),
    onSuccess: async () => {
      toast.success("Task deleted");
      setDeleting(null);
      await invalidateCrm(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const dialogs = (
    <>
      <TaskDialog
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
        timeZone={timeZone}
        {...(editing !== null && editing !== "new" ? { task: editing } : {})}
        {...(defaults ? { defaults } : {})}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={`Delete "${deleting?.title ?? "task"}"?`}
        description="This cannot be undone."
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </>
  );

  return {
    setStatus: (task, next) => status.mutate({ task, status: next }),
    pendingStatusId: status.isPending ? status.variables.task.id : null,
    openCreate: () => setEditing("new"),
    openEdit: setEditing,
    confirmDelete: setDeleting,
    dialogs,
  };
}
