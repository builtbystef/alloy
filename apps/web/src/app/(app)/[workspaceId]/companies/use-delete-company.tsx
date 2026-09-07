"use client";

import type { CompanyRef } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { companyKeys, invalidateCrm } from "@/lib/queries";
import { useWorkspace } from "@/lib/workspace";

export function useDeleteCompany({ onDeleted }: { onDeleted?: () => void } = {}): {
  confirmDelete: (company: CompanyRef) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [target, setTarget] = useState<CompanyRef | null>(null);

  const mutation = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}/companies/{company_id}", {
          params: { path: { workspace_id: workspaceId, company_id: id } },
        }),
      ),
    onSuccess: async (_, id) => {
      toast.success("Company deleted");
      setTarget(null);
      queryClient.removeQueries({ queryKey: companyKeys.detail(workspaceId, id) });
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
      title={`Delete ${target?.name ?? "company"}?`}
      description="Its contacts and tasks are kept; they just lose the link."
      pending={mutation.isPending}
      onConfirm={() => target && mutation.mutate(target.id)}
    />
  );

  return { confirmDelete: setTarget, dialog };
}
