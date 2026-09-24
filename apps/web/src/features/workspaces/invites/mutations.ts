import type { InviteCreate, InviteResponse, WorkspaceResponse } from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function createInvite(ws: string, body: InviteCreate): Promise<InviteResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/invites", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

/** A fresh link; the previous one stops working. */
export async function resendInvite(ws: string, inviteId: string): Promise<InviteResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/invites/{invite_id}/resend", {
      params: { path: { workspace_id: ws, invite_id: inviteId } },
    }),
  );
}

export async function revokeInvite(ws: string, inviteId: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/invites/{invite_id}", {
      params: { path: { workspace_id: ws, invite_id: inviteId } },
    }),
  );
}

/** Take the seat an emailed link offers; answers with the workspace joined. */
export async function acceptInvite(token: string): Promise<WorkspaceResponse> {
  return unwrap(await browserApi.POST("/invites/{token}/accept", { params: { path: { token } } }));
}

/** Without the link: one of the caller's own. */
export async function acceptPendingInvite(inviteId: string): Promise<WorkspaceResponse> {
  return unwrap(
    await browserApi.POST("/invites/pending/{invite_id}/accept", {
      params: { path: { invite_id: inviteId } },
    }),
  );
}

export async function declinePendingInvite(inviteId: string): Promise<void> {
  unwrap(
    await browserApi.POST("/invites/pending/{invite_id}/decline", {
      params: { path: { invite_id: inviteId } },
    }),
  );
}
