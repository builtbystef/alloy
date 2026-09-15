"use client";

import type { TaskCreate, TaskRead } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { createTask, updateTask } from "@/features/crm/tasks/mutations";
import {
  Form,
  FormActions,
  FormError,
  FormSection,
  FormSections,
  useAppForm,
} from "@/components/shared/form";
import { Button } from "@/components/ui/button";
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

/**
 * Create and edit in one form. Values are the strings the inputs hold; the
 * Zod schema validates them and produces the request body on submit.
 */
export function TaskForm({
  task,
  defaults,
  timeZone,
}: {
  /** Editing this task; omit to create. */
  task?: TaskRead;
  /** The pre-selected link when creating from a contact or company page. */
  defaults?: TaskLink;
  timeZone: string;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const { id: workspaceId, paths } = useWorkspace();

  const mutation = useMutation({
    mutationFn: (body: TaskCreate) =>
      task ? updateTask(workspaceId, task.id, body) : createTask(workspaceId, body),
    onSuccess: async (saved) => {
      toast.success(task ? "Task updated" : "Task created");
      await invalidateCrm(queryClient);
      router.push(paths.task(saved.id));
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
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      const saved = await mutation.mutateAsync(schema.parse(value)).catch(() => null);
      // Next.js keeps this page mounted, hidden, after the navigation, so the
      // form is blank rather than full of the last task when opened again.
      if (saved && !task) formApi.reset();
    },
  });

  const discard = () => {
    form.reset();
    setServerError(null);
  };

  return (
    <Form form={form} warnOnLeave>
      <FormError message={serverError} />
      <FormSections>
        <FormSection title="Details" description="Something to do, with a date to do it by.">
          <form.AppField name="title">
            {(field) => (
              <field.TextField
                label="Title"
                required
                placeholder="Send the proposal"
                autoComplete="off"
                autoFocus={!task}
              />
            )}
          </form.AppField>
          <div className="grid gap-5 sm:grid-cols-2">
            <form.AppField name="due_at">
              {(field) => <field.DateTimeField label="Due" />}
            </form.AppField>
            {/* A new task is open; the choice only matters once it exists. */}
            {task && (
              <form.AppField name="status">
                {(field) => (
                  <field.SelectField
                    label="Status"
                    options={statusOptions}
                    description="Marking a task done logs an activity on its contact."
                  />
                )}
              </form.AppField>
            )}
          </div>
        </FormSection>
        <FormSection title="Related to" description="The task shows up on their page.">
          <form.AppField name="related">
            {(field) => (
              <field.ComboboxField
                label="Contact or company"
                placeholder="Search contacts and companies"
                selected={task ? taskLinkOption(task) : undefined}
                search={(q) => taskLinkPickerQuery(browserApi, workspaceId, q)}
                resolve={(key) => taskLinkQuery(browserApi, workspaceId, key)}
              />
            )}
          </form.AppField>
        </FormSection>
        <FormSection title="Notes" description="Anything to remember when you get to it.">
          <form.AppField name="notes">
            {(field) => (
              <field.TextareaField
                label="Notes"
                rows={5}
                placeholder="They asked for pricing on the annual plan; include the discount."
              />
            )}
          </form.AppField>
        </FormSection>
      </FormSections>
      <FormActions className="border-t pt-8">
        <Button
          variant="outline"
          nativeButton={false}
          render={<Link href={task ? paths.task(task.id) : paths.tasks} onClick={discard} />}
        >
          Cancel
        </Button>
        <form.AppForm>
          <form.SubmitButton requireChanges={task !== undefined}>
            {task ? "Save changes" : "Create task"}
          </form.SubmitButton>
        </form.AppForm>
      </FormActions>
    </Form>
  );
}
