import { createFormHook } from "@tanstack/react-form";

import { fieldContext, formContext } from "./contexts";
import { DateTimeField, SelectField, TextareaField, TextField } from "./fields";
import { SubmitButton } from "./submit-button";

/**
 * `useAppForm` is `useForm` with the field components in ./fields and the
 * submit button pre-bound, per the TanStack Form "form composition" guide.
 * Forms validate with a Zod schema passed as `validators.onDynamic` and
 * `validationLogic: revalidateLogic()`: quiet until the first submit, then
 * live on every change.
 */
export const { useAppForm, withForm } = createFormHook({
  fieldContext,
  formContext,
  fieldComponents: { TextField, TextareaField, SelectField, DateTimeField },
  formComponents: { SubmitButton },
});

export { FormError } from "./form-error";
export type { SelectOption } from "./fields";
