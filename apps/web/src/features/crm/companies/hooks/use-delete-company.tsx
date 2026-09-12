"use client";

import type { CompanyRef } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { deleteCompany } from "@/features/crm/companies/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { errorMessage } from "@/lib/api/errors";
import { companyKeys } from "@/features/crm/companies/queries";
import { invalidateCrm } from "@/features/crm/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

export function useDeleteCompany({ onDeleted }: { onDeleted?: () => void } = {}): {
  confirmDelete: (company: CompanyRef) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [target, setTarget] = useState<CompanyRef | null>(null);

  const mutation = useMutation({
    mutationFn: (id: string) => deleteCompany(workspaceId, id),
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
