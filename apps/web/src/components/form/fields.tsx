"use client";

import type { ComponentProps } from "react";

import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";

import { useFieldContext } from "./contexts";

/**
 * Field components bound to the form through `createFormHook`, so a form
 * renders `<form.AppField name="email">{(f) => <f.TextField label="Email" />}</form.AppField>`
 * and the wiring of value, change, blur, and errors lives here once.
 */

interface CommonProps {
  label: string;
  description?: string;
}

function useFieldState() {
  const field = useFieldContext<string>();
  const invalid = field.state.meta.isTouched && !field.state.meta.isValid;
  return { field, invalid };
}

export function TextField({
  label,
  description,
  ...inputProps
}: CommonProps &
  Omit<ComponentProps<typeof Input>, "value" | "onChange" | "onBlur" | "id" | "name">) {
  const { field, invalid } = useFieldState();
  return (
    <Field data-invalid={invalid}>
      <FieldLabel htmlFor={field.name}>{label}</FieldLabel>
      <Input
        id={field.name}
        name={field.name}
        value={field.state.value}
        onBlur={field.handleBlur}
        onChange={(event) => field.handleChange(event.target.value)}
        aria-invalid={invalid}
        {...inputProps}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
      {invalid && <FieldError errors={field.state.meta.errors} />}
    </Field>
  );
}

export function TextareaField({
  label,
  description,
  ...textareaProps
}: CommonProps &
  Omit<ComponentProps<typeof Textarea>, "value" | "onChange" | "onBlur" | "id" | "name">) {
  const { field, invalid } = useFieldState();
  return (
    <Field data-invalid={invalid}>
      <FieldLabel htmlFor={field.name}>{label}</FieldLabel>
      <Textarea
        id={field.name}
        name={field.name}
        value={field.state.value}
        onBlur={field.handleBlur}
        onChange={(event) => field.handleChange(event.target.value)}
        aria-invalid={invalid}
        {...textareaProps}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
      {invalid && <FieldError errors={field.state.meta.errors} />}
    </Field>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export function SelectField({
  label,
  description,
  options,
  placeholder,
  disabled,
}: CommonProps & {
  options: readonly SelectOption[];
  /** Adds an empty option with this label, which the schema turns into null. */
  placeholder?: string;
  disabled?: boolean;
}) {
  const { field, invalid } = useFieldState();
  return (
    <Field data-invalid={invalid}>
      <FieldLabel htmlFor={field.name}>{label}</FieldLabel>
      <NativeSelect
        id={field.name}
        name={field.name}
        value={field.state.value}
        onBlur={field.handleBlur}
        onChange={(event) => field.handleChange(event.target.value)}
        aria-invalid={invalid}
        disabled={disabled}
        className="w-full"
      >
        {placeholder !== undefined && (
          <NativeSelectOption value="">{placeholder}</NativeSelectOption>
        )}
        {options.map((option) => (
          <NativeSelectOption key={option.value} value={option.value}>
            {option.label}
          </NativeSelectOption>
        ))}
      </NativeSelect>
      {description && <FieldDescription>{description}</FieldDescription>}
      {invalid && <FieldError errors={field.state.meta.errors} />}
    </Field>
  );
}

export function DateTimeField({ label, description }: CommonProps) {
  const { field, invalid } = useFieldState();
  return (
    <Field data-invalid={invalid}>
      <FieldLabel htmlFor={field.name}>{label}</FieldLabel>
      <Input
        id={field.name}
        name={field.name}
        type="datetime-local"
        value={field.state.value}
        onBlur={field.handleBlur}
        onChange={(event) => field.handleChange(event.target.value)}
        aria-invalid={invalid}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
      {invalid && <FieldError errors={field.state.meta.errors} />}
    </Field>
  );
}
