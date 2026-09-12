"use client";

import type { ActivityCreate, ActivityType } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import {
  CheckCircle2Icon,
  MailIcon,
  MessageSquareTextIcon,
  PhoneIcon,
  RepeatIcon,
  UsersIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { logActivity } from "@/features/crm/contacts/mutations";
import { FormError, useAppForm } from "@/components/shared/form";
import { TruncatedNote } from "@/components/shared/truncated-note";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { formatDateTime, formatRelativeDays } from "@/lib/formatting/dates";
import { activityTypeLabels } from "@/features/crm/contacts/labels";
import { contactActivitiesQuery } from "@/features/crm/contacts/queries";
import { invalidateCrm } from "@/features/crm/queries";
import {
  activitySchema,
  loggableActivityTypes,
  type ActivityInput,
} from "@/features/crm/contacts/schemas";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

const icons: Record<ActivityType, ReactNode> = {
  note: <MessageSquareTextIcon />,
  call: <PhoneIcon />,
  email: <MailIcon />,
  meeting: <UsersIcon />,
  follow_up: <RepeatIcon />,
  task_completed: <CheckCircle2Icon />,
};

const typeOptions = loggableActivityTypes.map((value) => ({
  value,
  label: activityTypeLabels[value],
}));

export function ActivityFeed({ contactId, timeZone }: { contactId: string; timeZone: string }) {
  const { id: workspaceId } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: activities } = useSuspenseQuery(
    contactActivitiesQuery(browserApi, workspaceId, contactId),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>
          Calls, emails, meetings, and follow-ups update when this contact was last reached.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {canWrite && <LogActivityForm contactId={contactId} />}
        {activities.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing logged yet.</p>
        ) : (
          <ol className="flex flex-col gap-4">
            {activities.items.map((activity) => (
              <li key={activity.id} className="flex gap-3">
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-3.5">
                  {icons[activity.type]}
                </span>
                <div className="flex min-w-0 flex-col gap-0.5">
                  <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
                    <span className="font-medium">{activityTypeLabels[activity.type]}</span>
                    <span className="text-xs text-muted-foreground">
                      <span title={formatDateTime(activity.created_at, timeZone)}>
                        {formatRelativeDays(activity.created_at, timeZone)}
                      </span>
                      {activity.created_by && ` by ${activity.created_by.email}`}
                    </span>
                  </div>
                  {activity.notes && (
                    <p className="text-sm whitespace-pre-wrap text-muted-foreground">
                      {activity.notes}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        <TruncatedNote shown={activities.items.length} total={activities.total} noun="activities" />
      </CardContent>
    </Card>
  );
}

function LogActivityForm({ contactId }: { contactId: string }) {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: ActivityCreate) => logActivity(workspaceId, contactId, body),
    onSuccess: async () => {
      toast.success("Activity logged");
      await invalidateCrm(queryClient);
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { type: "note", notes: "" } as ActivityInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: activitySchema },
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      await mutation.mutateAsync(activitySchema.parse(value)).then(
        () => formApi.reset(),
        () => {}, // shown through onError
      );
    },
  });

  return (
    <form
      className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="type">
          {(field) => <field.SelectField label="Type" options={typeOptions} />}
        </form.AppField>
        <form.AppField name="notes">
          {(field) => <field.TextareaField label="Notes" rows={3} placeholder="What happened?" />}
        </form.AppField>
      </FieldGroup>
      <form.AppForm>
        <form.SubmitButton className="self-start">Log activity</form.SubmitButton>
      </form.AppForm>
    </form>
  );
}
