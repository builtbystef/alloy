"use client";

import type { ContactRef } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { deleteContact } from "@/features/crm/contacts/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { errorMessage } from "@/lib/api/errors";
import { contactKeys } from "@/features/crm/contacts/queries";
import { invalidateCrm } from "@/features/crm/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

/** A confirm-then-delete flow; render `dialog` once near the list. */
export function useDeleteContact({ onDeleted }: { onDeleted?: () => void } = {}): {
  confirmDelete: (contact: ContactRef) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [target, setTarget] = useState<ContactRef | null>(null);

  const mutation = useMutation({
    mutationFn: (id: string) => deleteContact(workspaceId, id),
    onSuccess: async (_, id) => {
      toast.success("Contact deleted");
      setTarget(null);
      queryClient.removeQueries({ queryKey: contactKeys.detail(workspaceId, id) });
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
