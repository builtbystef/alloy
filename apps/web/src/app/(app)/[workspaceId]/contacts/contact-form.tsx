"use client";

import type { ContactCreate, ContactRead } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, useAppForm } from "@/components/form";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { isoToWallClock } from "@/lib/dates";
import { contactStatusLabels } from "@/lib/labels";
import { companyPickerQuery, companyQuery, invalidateCrm } from "@/lib/queries";
import { contactSchema, contactStatuses, type ContactInput } from "@/lib/schemas";
import { useWorkspace } from "@/lib/workspace";

const statusOptions = contactStatuses.map((value) => ({
  value,
  label: contactStatusLabels[value],
}));

/**
 * Create and edit in one form. Values are the strings the inputs hold; the
 * Zod schema validates them and produces the request body on submit.
 */
export function ContactForm({
  contact,
  defaultCompanyId,
  timeZone,
}: {
  /** Editing this contact; omit to create. */
  contact?: ContactRead;
  defaultCompanyId?: string;
  timeZone: string;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const { id: workspaceId, paths } = useWorkspace();

  const mutation = useMutation({
    mutationFn: async (body: ContactCreate) =>
      contact
        ? unwrap(
            await browserApi.PATCH("/workspaces/{workspace_id}/contacts/{contact_id}", {
              params: { path: { workspace_id: workspaceId, contact_id: contact.id } },
              body,
            }),
          )
        : unwrap(
            await browserApi.POST("/workspaces/{workspace_id}/contacts/", {
              params: { path: { workspace_id: workspaceId } },
              body,
            }),
          ),
    onSuccess: async (saved) => {
      toast.success(contact ? "Contact updated" : "Contact created");
      await invalidateCrm(queryClient);
      router.push(paths.contact(saved.id));
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const schema = contactSchema(timeZone);
  const form = useAppForm({
    defaultValues: {
      name: contact?.name ?? "",
      email: contact?.email ?? "",
      phone: contact?.phone ?? "",
      job_title: contact?.job_title ?? "",
      company_id: contact?.company?.id ?? defaultCompanyId ?? "",
      status: contact?.status ?? "lead",
      last_contacted_at: isoToWallClock(contact?.last_contacted_at, timeZone),
    } satisfies ContactInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: schema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(schema.parse(value)).catch(() => {});
    },
  });

  return (
    <form
      className="flex max-w-xl flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="name">
          {(field) => <field.TextField label="Name" autoFocus={!contact} />}
        </form.AppField>
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="email">
            {(field) => <field.TextField label="Email" type="email" autoComplete="off" />}
          </form.AppField>
          <form.AppField name="phone">
            {(field) => <field.TextField label="Phone" type="tel" autoComplete="off" />}
          </form.AppField>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="job_title">
            {(field) => <field.TextField label="Job title" />}
          </form.AppField>
          <form.AppField name="company_id">
            {(field) => (
              <field.ComboboxField
                label="Company"
                placeholder="No company"
                selected={contact?.company}
                search={(q) => companyPickerQuery(browserApi, workspaceId, q)}
                resolve={(id) => companyQuery(browserApi, workspaceId, id)}
              />
            )}
          </form.AppField>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="status">
            {(field) => <field.SelectField label="Status" options={statusOptions} />}
          </form.AppField>
          <form.AppField name="last_contacted_at">
            {(field) => (
              <field.DateTimeField
                label="Last contacted"
                description="Logging a call, email, or meeting updates this by itself."
              />
            )}
          </form.AppField>
        </div>
      </FieldGroup>
      <div className="flex items-center gap-2">
        <form.AppForm>
          <form.SubmitButton>{contact ? "Save changes" : "Create contact"}</form.SubmitButton>
        </form.AppForm>
        <Button
          variant="ghost"
          nativeButton={false}
          render={<Link href={contact ? paths.contact(contact.id) : paths.contacts} />}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
