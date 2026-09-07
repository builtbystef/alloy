"use client";

import type { WorkspaceRead } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";
import { WORKSPACE_COOKIE } from "@/lib/workspace-shared";

/** Leave or delete the workspace. Both send the user back to `/` to pick another. */
export function DangerZone({ workspace }: { workspace: WorkspaceRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState<"leave" | "delete" | null>(null);
  const canDelete = workspace.permissions.includes("workspace:delete");

  const done = (message: string) => {
    toast.success(message);
    // Forget it, so `/` does not try to reopen it.
    document.cookie = `${WORKSPACE_COOKIE}=; Path=/; Max-Age=0`;
    queryClient.clear();
    router.push("/");
    router.refresh();
  };

  const failed = (error: unknown) => {
    setConfirming(null);
    toast.error(
      error instanceof ApiError && error.status === 409
        ? "You are the only owner. Make someone else an owner first, or delete the workspace."
        : errorMessage(error),
    );
  };

  const leave = useMutation({
    mutationFn: async () =>
      unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/leave", {
          params: { path: { workspace_id: workspace.id } },
        }),
      ),
    onSuccess: () => done(`You left ${workspace.name}`),
    onError: failed,
  });

  const remove = useMutation({
    mutationFn: async () =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}", {
          params: { path: { workspace_id: workspace.id } },
        }),
      ),
    onSuccess: () => done(`Deleted ${workspace.name}`),
    onError: failed,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Danger zone</CardTitle>
        <CardDescription>Neither of these can be undone.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-4">
        <div className="flex flex-col gap-2">
          <Button variant="outline" onClick={() => setConfirming("leave")}>
            Leave workspace
          </Button>
          <p className="text-sm text-muted-foreground">
            You lose access; everything else stays. The last owner cannot leave.
          </p>
        </div>
        {canDelete && (
          <div className="flex flex-col gap-2">
            <Button variant="destructive" onClick={() => setConfirming("delete")}>
              Delete workspace
            </Button>
            <p className="text-sm text-muted-foreground">
              Removes every contact, company, task, member, and invitation in it.
            </p>
          </div>
        )}
      </CardContent>
      <ConfirmDialog
        open={confirming === "leave"}
        onOpenChange={(open) => {
          if (!open) setConfirming(null);
        }}
        title={`Leave ${workspace.name}?`}
        description="You will need a new invitation to come back."
        confirmLabel="Leave"
        pending={leave.isPending}
        onConfirm={() => leave.mutate()}
      />
      <ConfirmDialog
        open={confirming === "delete"}
        onOpenChange={(open) => {
          if (!open) setConfirming(null);
        }}
        title={`Delete ${workspace.name}?`}
        description="Every record and every member's access goes with it. This cannot be undone."
        pending={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </Card>
  );
}
