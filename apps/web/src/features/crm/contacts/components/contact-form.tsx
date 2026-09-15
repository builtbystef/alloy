"use client";

import type { ContactCreate, ContactRead } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { createContact, updateContact } from "@/features/crm/contacts/mutations";
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
import { contactStatusLabels } from "@/features/crm/contacts/labels";
import { companyPickerQuery, companyQuery } from "@/features/crm/companies/queries";
import { invalidateCrm } from "@/features/crm/queries";
import { contactSchema, contactStatuses, type ContactInput } from "@/features/crm/contacts/schemas";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

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
    mutationFn: (body: ContactCreate) =>
      contact ? updateContact(workspaceId, contact.id, body) : createContact(workspaceId, body),
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
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      const saved = await mutation.mutateAsync(schema.parse(value)).catch(() => null);
      // Next.js keeps this page mounted, hidden, after the navigation, so the
      // form is blank rather than full of the last contact when opened again.
      if (saved && !contact) formApi.reset();
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
        <FormSection
          title="Details"
          description="
          Only the name is required. Add the rest as you learn it.
        "
        >
          <form.AppField name="name">
            {(field) => (
              <field.TextField
                label="Name"
                required
                placeholder="Jane Doe"
                autoComplete="off"
                autoFocus={!contact}
              />
            )}
          </form.AppField>
          <div className="grid gap-5 sm:grid-cols-2">
            <form.AppField name="email">
              {(field) => (
                <field.TextField
                  label="Email"
                  type="email"
                  placeholder="jane@example.com"
                  autoComplete="off"
                />
              )}
            </form.AppField>
            <form.AppField name="phone">
              {(field) => (
                <field.TextField
                  label="Phone"
                  type="tel"
                  placeholder="+1 555 0100"
                  autoComplete="off"
                />
              )}
            </form.AppField>
          </div>
        </FormSection>
        <FormSection title="Work" description="Where they work and what they do there.">
          <div className="grid gap-5 sm:grid-cols-2">
            <form.AppField name="company_id">
              {(field) => (
                <field.ComboboxField
                  label="Company"
                  placeholder="Search companies"
                  selected={contact?.company}
                  search={(q) => companyPickerQuery(browserApi, workspaceId, q)}
                  resolve={(id) => companyQuery(browserApi, workspaceId, id)}
                />
              )}
            </form.AppField>
            <form.AppField name="job_title">
              {(field) => <field.TextField label="Job title" placeholder="Head of Sales" />}
            </form.AppField>
          </div>
        </FormSection>
        <FormSection title="Relationship" description="Where things stand with this contact.">
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
        </FormSection>
      </FormSections>
      <FormActions className="border-t pt-8">
        <Button
          variant="outline"
          nativeButton={false}
          render={
            <Link href={contact ? paths.contact(contact.id) : paths.contacts} onClick={discard} />
          }
        >
          Cancel
        </Button>
        <form.AppForm>
          <form.SubmitButton requireChanges={contact !== undefined}>
            {contact ? "Save changes" : "Create contact"}
          </form.SubmitButton>
        </form.AppForm>
      </FormActions>
    </Form>
  );
}
