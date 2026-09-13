"use client";

import type { TaskCreate, TaskRead } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { createTask, updateTask } from "@/features/crm/tasks/mutations";
import { FormError, useAppForm } from "@/components/shared/form";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { isoToWallClock } from "@/lib/formatting/dates";
import { taskStatusLabels } from "@/features/crm/tasks/labels";
import { invalidateCrm } from "@/features/crm/queries";
import { linkKey, taskLinkOption, type TaskLink } from "@/features/crm/tasks/links";
import { taskLinkPickerQuery, taskLinkQuery } from "@/features/crm/tasks/queries";
import { taskSchema, taskStatuses, type TaskInput } from "@/features/crm/tasks/schemas";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

const statusOptions = taskStatuses.map((value) => ({ value, label: taskStatusLabels[value] }));

export interface TaskFormProps {
  /** Editing this task; omit to create. */
  task?: TaskRead;
  /** The pre-selected link when creating from a contact or company page. */
  defaults?: TaskLink;
  timeZone: string;
  onSaved: () => void;
  onCancel: () => void;
}

export function TaskForm({ task, defaults, timeZone, onSaved, onCancel }: TaskFormProps) {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const { id: workspaceId } = useWorkspace();

  const mutation = useMutation({
    mutationFn: (body: TaskCreate) =>
      task ? updateTask(workspaceId, task.id, body) : createTask(workspaceId, body),
    onSuccess: async () => {
      toast.success(task ? "Task updated" : "Task created");
      await invalidateCrm(queryClient);
      onSaved();
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const schema = taskSchema(timeZone);
  const form = useAppForm({
    defaultValues: {
      title: task?.title ?? "",
      due_at: isoToWallClock(task?.due_at, timeZone),
      status: task?.status ?? "open",
      related: task ? (taskLinkOption(task)?.id ?? "") : linkKey(defaults),
      notes: task?.notes ?? "",
    } satisfies TaskInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: schema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(schema.parse(value)).catch(() => {});
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
        <form.AppField name="title">
          {(field) => <field.TextField label="Title" autoFocus />}
        </form.AppField>
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="due_at">
            {(field) => <field.DateTimeField label="Due" />}
          </form.AppField>
          <form.AppField name="status">
            {(field) => <field.SelectField label="Status" options={statusOptions} />}
          </form.AppField>
        </div>
        <form.AppField name="related">
          {(field) => (
            <field.ComboboxField
              label="Related to"
              placeholder="No contact or company"
              selected={task ? taskLinkOption(task) : undefined}
              search={(q) => taskLinkPickerQuery(browserApi, workspaceId, q)}
              resolve={(key) => taskLinkQuery(browserApi, workspaceId, key)}
            />
          )}
        </form.AppField>
        <form.AppField name="notes">
          {(field) => <field.TextareaField label="Notes" rows={3} />}
        </form.AppField>
      </FieldGroup>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <form.AppForm>
          <form.SubmitButton>{task ? "Save changes" : "Create task"}</form.SubmitButton>
        </form.AppForm>
      </div>
    </form>
  );
}
