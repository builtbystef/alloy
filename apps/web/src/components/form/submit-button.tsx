"use client";

import { Loader2Icon } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

import { useFormContext } from "./contexts";

export function SubmitButton({
  children,
  className,
  disabled = false,
}: {
  children: ReactNode;
  className?: string;
  /** Beyond "while submitting": when the form can no longer succeed. */
  disabled?: boolean;
}) {
  const form = useFormContext();
  return (
    <form.Subscribe selector={(state) => state.isSubmitting}>
      {(isSubmitting) => (
        <Button type="submit" disabled={disabled || isSubmitting} className={className}>
          {isSubmitting && <Loader2Icon className="animate-spin" />}
          {children}
        </Button>
      )}
    </form.Subscribe>
  );
}
