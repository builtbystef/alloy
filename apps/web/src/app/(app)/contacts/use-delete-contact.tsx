"use client";

import type { ContactRef } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { invalidateCrm } from "@/lib/queries";

/** A confirm-then-delete flow; render `dialog` once near the list. */
export function useDeleteContact({ onDeleted }: { onDeleted?: () => void } = {}): {
  confirmDelete: (contact: ContactRef) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<ContactRef | null>(null);

  const mutation = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE("/contacts/{contact_id}", { params: { path: { contact_id: id } } }),
      ),
    onSuccess: async (_, id) => {
      toast.success("Contact deleted");
      setTarget(null);
      queryClient.removeQueries({ queryKey: ["contacts", "detail", id] });
      await invalidateCrm(queryClient);
      onDeleted?.();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const dialog = (
    <ConfirmDialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open) setTarget(null);
      }}
      title={`Delete ${target?.name ?? "contact"}?`}
      description="The activity feed goes with it. Tasks are kept and unlinked."
      pending={mutation.isPending}
      onConfirm={() => target && mutation.mutate(target.id)}
    />
  );

  return { confirmDelete: setTarget, dialog };
}
