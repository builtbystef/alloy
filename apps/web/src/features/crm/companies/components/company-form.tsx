"use client";

import type { CompanyCreate, CompanyResponse } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { createCompany, updateCompany } from "@/features/crm/companies/mutations";
import {
  Form,
  FormActions,
  FormError,
  FormSection,
  FormSections,
  useAppForm,
} from "@/components/shared/form";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { invalidateCrm } from "@/features/crm/queries";
import { companySchema, type CompanyInput } from "@/features/crm/companies/schemas";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

export function CompanyForm({ company }: { company?: CompanyResponse }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const { id: workspaceId, paths } = useWorkspace();

  const mutation = useMutation({
    mutationFn: (body: CompanyCreate) =>
      company ? updateCompany(workspaceId, company.id, body) : createCompany(workspaceId, body),
    onSuccess: async (saved) => {
      toast.success(company ? "Company updated" : "Company created");
      await invalidateCrm(queryClient);
      router.push(paths.company(saved.id));
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: {
      name: company?.name ?? "",
      website: company?.website ?? "",
      industry: company?.industry ?? "",
      notes: company?.notes ?? "",
    } satisfies CompanyInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: companySchema },
    onSubmit: async ({ value, formApi }) => {
      setServerError(null);
      const saved = await mutation.mutateAsync(companySchema.parse(value)).catch(() => null);
      // Next.js keeps this page mounted, hidden, after the navigation, so the
      // form is blank rather than full of the last company when opened again.
      if (saved && !company) formApi.reset();
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
                placeholder="Acme Inc."
                autoComplete="off"
                autoFocus={!company}
              />
            )}
          </form.AppField>
          <div className="grid gap-5 sm:grid-cols-2">
            <form.AppField name="website">
              {(field) => (
                <field.TextField
                  label="Website"
                  type="url"
                  placeholder="https://acme.com"
                  autoComplete="off"
                />
              )}
            </form.AppField>
            <form.AppField name="industry">
              {(field) => <field.TextField label="Industry" placeholder="Software" />}
            </form.AppField>
          </div>
        </FormSection>
        <FormSection title="Notes" description="Anything the team should know about this company.">
          <form.AppField name="notes">
            {(field) => (
              <field.TextareaField
                label="Notes"
                rows={5}
                placeholder="Met at the trade show; they are moving off their old vendor in Q3."
              />
            )}
          </form.AppField>
        </FormSection>
      </FormSections>
      <FormActions className="border-t pt-8">
        <Button
          variant="outline"
          nativeButton={false}
          render={
            <Link href={company ? paths.company(company.id) : paths.companies} onClick={discard} />
          }
        >
          Cancel
        </Button>
        <form.AppForm>
          <form.SubmitButton requireChanges={company !== undefined}>
            {company ? "Save changes" : "Create company"}
          </form.SubmitButton>
        </form.AppForm>
      </FormActions>
    </Form>
  );
}
