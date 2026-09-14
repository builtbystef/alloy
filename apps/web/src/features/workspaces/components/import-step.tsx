"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { completeOnboarding } from "@/features/workspaces/mutations";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { invalidateWorkspaces } from "@/features/workspaces/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

import { ImportCard } from "@/features/crm/imports/components/import-card";
import { ImportsTable } from "@/features/crm/imports/components/imports-table";

/** Imports run in the background, so both buttons finish onboarding at once. */
export function ImportStep({ timeZone }: { timeZone: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspace = useWorkspace();

  const finish = useMutation({
    mutationFn: () => completeOnboarding(workspace.id),
    onSuccess: async () => {
      await invalidateWorkspaces(queryClient);
      router.push(workspace.paths.home);
      router.refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <div className="flex flex-col gap-6">
      <ImportCard initialKind="contacts" />
      <ImportsTable timeZone={timeZone} />
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => finish.mutate()} disabled={finish.isPending}>
          {finish.isPending && <Loader2Icon className="animate-spin" />}
          Continue to {workspace.name}
        </Button>
        <Button variant="ghost" onClick={() => finish.mutate()} disabled={finish.isPending}>
          Skip for now
        </Button>
      </div>
    </div>
  );
}
