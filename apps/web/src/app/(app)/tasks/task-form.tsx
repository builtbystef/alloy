"use client";

import type { TaskCreate, TaskRead } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { isoToWallClock } from "@/lib/dates";
import { taskStatusLabels } from "@/lib/labels";
import { companyListQuery, contactListQuery, invalidateCrm } from "@/lib/queries";
import { taskSchema, taskStatuses, type TaskInput } from "@/lib/schemas";

const statusOptions = taskStatuses.map((value) => ({ value, label: taskStatusLabels[value] }));

export interface TaskFormProps {
  /** Editing this task; omit to create. */
  task?: TaskRead;
  /** Pre-selected links when creating from a contact or company page. */
  defaults?: { contact_id?: string; company_id?: string };
  timeZone: string;
  onSaved: () => void;
  onCancel: () => void;
}

export function TaskForm({ task, defaults, timeZone, onSaved, onCancel }: TaskFormProps) {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const contacts = useQuery(contactListQuery(browserApi, {}));
  const companies = useQuery(companyListQuery(browserApi, {}));

  const mutation = useMutation({
    mutationFn: async (body: TaskCreate) =>
      task
        ? unwrap(
            await browserApi.PATCH("/tasks/{task_id}", {
              params: { path: { task_id: task.id } },
              body,
            }),
          )
        : unwrap(await browserApi.POST("/tasks/", { body })),
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
      contact_id: task?.contact?.id ?? defaults?.contact_id ?? "",
      company_id: task?.company?.id ?? defaults?.company_id ?? "",
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
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="contact_id">
            {(field) => (
              <field.SelectField
                label="Contact"
                placeholder={contacts.isPending ? "Loading…" : "No contact"}
                options={(contacts.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
                disabled={contacts.isPending}
              />
            )}
          </form.AppField>
          <form.AppField name="company_id">
            {(field) => (
              <field.SelectField
                label="Company"
                placeholder={companies.isPending ? "Loading…" : "No company"}
                options={(companies.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
                disabled={companies.isPending}
              />
            )}
          </form.AppField>
        </div>
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
