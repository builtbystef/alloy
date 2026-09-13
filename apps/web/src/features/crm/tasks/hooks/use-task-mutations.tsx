"use client";

import type { TaskRead, TaskStatus } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { deleteTask, updateTask } from "@/features/crm/tasks/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { errorMessage } from "@/lib/api/errors";
import { invalidateCrm } from "@/features/crm/queries";
import { taskKeys } from "@/features/crm/tasks/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

/**
 * What a task row or page can do in place: toggle done, and delete after
 * confirming. Creating and editing are pages. Render `dialog` once near the list.
 */
export function useTaskMutations({ onDeleted }: { onDeleted?: () => void } = {}): {
  setStatus: (task: TaskRead, status: TaskStatus) => void;
  pendingStatusId: string | null;
  confirmDelete: (task: TaskRead) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
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
    onSuccess: async (_, id) => {
      toast.success("Task deleted");
      setDeleting(null);
      queryClient.removeQueries({ queryKey: taskKeys.detail(workspaceId, id) });
      await invalidateCrm(queryClient);
      onDeleted?.();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const dialog = (
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
  );

  return {
    setStatus: (task, next) => status.mutate({ task, status: next }),
    pendingStatusId: status.isPending ? status.variables.task.id : null,
    confirmDelete: setDeleting,
    dialog,
  };
}
