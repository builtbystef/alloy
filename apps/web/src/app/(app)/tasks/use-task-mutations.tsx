"use client";

import type { TaskRead, TaskStatus } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { invalidateCrm } from "@/lib/queries";

import { TaskDialog } from "./task-dialog";

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
  const [editing, setEditing] = useState<TaskRead | "new" | null>(null);
  const [deleting, setDeleting] = useState<TaskRead | null>(null);

  const status = useMutation({
    mutationFn: async ({ task, status }: { task: TaskRead; status: TaskStatus }) =>
      unwrap(
        await browserApi.PATCH("/tasks/{task_id}", {
          params: { path: { task_id: task.id } },
          body: { status },
        }),
      ),
    onSuccess: async (saved) => {
      if (saved.status === "done") toast.success("Task completed");
      await invalidateCrm(queryClient);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const remove = useMutation({
    mutationFn: async (id: string) =>
      unwrap(await browserApi.DELETE("/tasks/{task_id}", { params: { path: { task_id: id } } })),
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
