"use client";

import type { CompanyCreate, CompanyRead } from "@alloy/api-client";
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
import { invalidateCrm } from "@/lib/queries";
import { companySchema, type CompanyInput } from "@/lib/schemas";
import { useWorkspace } from "@/lib/workspace";

export function CompanyForm({ company }: { company?: CompanyRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const { id: workspaceId, paths } = useWorkspace();

  const mutation = useMutation({
    mutationFn: async (body: CompanyCreate) =>
      company
        ? unwrap(
            await browserApi.PATCH("/workspaces/{workspace_id}/companies/{company_id}", {
              params: { path: { workspace_id: workspaceId, company_id: company.id } },
              body,
            }),
          )
        : unwrap(
            await browserApi.POST("/workspaces/{workspace_id}/companies/", {
              params: { path: { workspace_id: workspaceId } },
              body,
            }),
          ),
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
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(companySchema.parse(value)).catch(() => {});
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
          {(field) => <field.TextField label="Name" autoFocus={!company} />}
        </form.AppField>
        <div className="grid gap-5 sm:grid-cols-2">
          <form.AppField name="website">
            {(field) => (
              <field.TextField
                label="Website"
                type="url"
                placeholder="https://"
                autoComplete="off"
              />
            )}
          </form.AppField>
          <form.AppField name="industry">
            {(field) => <field.TextField label="Industry" />}
          </form.AppField>
        </div>
        <form.AppField name="notes">
          {(field) => <field.TextareaField label="Notes" rows={4} />}
        </form.AppField>
      </FieldGroup>
      <div className="flex items-center gap-2">
        <form.AppForm>
          <form.SubmitButton>{company ? "Save changes" : "Create company"}</form.SubmitButton>
        </form.AppForm>
        <Button
          variant="ghost"
          nativeButton={false}
          render={<Link href={company ? paths.company(company.id) : paths.companies} />}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
