"use client";

import type { ProfileUpdate } from "@alloy/api-client";
import { revalidateLogic } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { updateProfile } from "@/features/auth/mutations";
import { Form, FormError, useAppForm } from "@/components/shared/form";
import { FieldGroup } from "@/components/ui/field";
import { errorMessage } from "@/lib/api/errors";
import { profileSchema, type ProfileInput } from "@/features/auth/schemas";

/** `name` comes from the server render, so `router.refresh()` updates it. */
export function NameForm({ name }: { name: string }) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (body: ProfileUpdate) => updateProfile(body),
    onSuccess: () => {
      toast.success("Name saved");
      // The name is rendered by Server Components (user menu), so refresh them.
      router.refresh();
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const form = useAppForm({
    defaultValues: { name } satisfies ProfileInput,
    validationLogic: revalidateLogic(),
    validators: { onDynamic: profileSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      await mutation.mutateAsync(profileSchema.parse(value)).catch(() => {});
    },
  });

  return (
    <Form form={form}>
      <FieldGroup>
        <FormError message={serverError} />
        <form.AppField name="name">
          {(field) => <field.TextField label="Name" autoComplete="name" />}
        </form.AppField>
      </FieldGroup>
      <form.AppForm>
        <form.SubmitButton className="self-start" requireChanges>
          Save
        </form.SubmitButton>
      </form.AppForm>
    </Form>
  );
}
