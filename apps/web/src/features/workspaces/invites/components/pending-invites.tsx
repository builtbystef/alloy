"use client";

import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { acceptPendingInvite, declinePendingInvite } from "@/features/workspaces/invites/mutations";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/formatting/dates";
import { roleLabels } from "@/features/workspaces/roles";
import { pendingInviteListQuery } from "@/features/workspaces/invites/queries";
import { invalidateWorkspaces } from "@/features/workspaces/queries";

/**
 * Accepting opens the workspace. With `whenEmpty="onboarding"`, declining the
 * last one goes on to create a workspace, and a link offers that anyway.
 */
export function PendingInvites({
  timeZone,
  whenEmpty = "stay",
}: {
  timeZone: string;
  whenEmpty?: "onboarding" | "stay";
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: invites } = useSuspenseQuery(pendingInviteListQuery(browserApi));

  const accept = useMutation({
    mutationFn: acceptPendingInvite,
    onSuccess: async (workspace) => {
      toast.success(`You joined ${workspace.name}`);
      queryClient.clear();
      router.push(`/${workspace.id}`);
      router.refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const decline = useMutation({
    mutationFn: declinePendingInvite,
    onSuccess: async (_, inviteId) => {
      toast.success("Invitation declined");
      await invalidateWorkspaces(queryClient);
      if (whenEmpty === "onboarding" && invites.every((invite) => invite.id === inviteId)) {
        router.push("/onboarding");
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const busy = accept.isPending || decline.isPending;

  return (
    <div className="flex flex-col gap-6">
      {invites.length === 0 ? (
        <p className="text-sm text-muted-foreground">No pending invitations.</p>
      ) : (
        <ul className="divide-y rounded-lg border px-4">
          {invites.map((invite) => (
            <li key={invite.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{invite.workspace_name}</p>
                <p className="text-sm text-muted-foreground">
                  {roleLabels[invite.role]}
                  {invite.invited_by && ` · invited by ${invite.invited_by}`}
                  {` · expires ${formatDate(invite.expires_at, timeZone)}`}
                </p>
              </div>
              <div className="flex gap-1">
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => accept.mutate(invite.id)}
                  aria-label={`Accept the invitation to ${invite.workspace_name}`}
                >
                  {accept.isPending && accept.variables === invite.id && (
                    <Loader2Icon className="animate-spin" />
                  )}
                  Accept
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busy}
                  onClick={() => decline.mutate(invite.id)}
                  aria-label={`Decline the invitation to ${invite.workspace_name}`}
                >
                  Decline
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {whenEmpty === "onboarding" && (
        <p className="text-sm text-muted-foreground">
          Not joining a team?{" "}
          <Link href="/onboarding" className="text-foreground underline underline-offset-4">
            Create your own workspace
          </Link>{" "}
          instead.
        </p>
      )}
    </div>
  );
}
