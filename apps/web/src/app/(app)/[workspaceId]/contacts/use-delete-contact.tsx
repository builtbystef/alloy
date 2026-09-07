"use client";

import type { ContactRef } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { contactKeys, invalidateCrm } from "@/lib/queries";
import { useWorkspace } from "@/lib/workspace";

/** A confirm-then-delete flow; render `dialog` once near the list. */
export function useDeleteContact({ onDeleted }: { onDeleted?: () => void } = {}): {
  confirmDelete: (contact: ContactRef) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [target, setTarget] = useState<ContactRef | null>(null);

  const mutation = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}/contacts/{contact_id}", {
          params: { path: { workspace_id: workspaceId, contact_id: id } },
        }),
      ),
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
