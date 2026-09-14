import type {
  InviteCreate,
  InviteRead,
  MemberRead,
  WorkspaceCreate,
  WorkspaceRead,
  WorkspaceRole,
  WorkspaceUpdate,
} from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function createWorkspace(body: WorkspaceCreate): Promise<WorkspaceRead> {
  return unwrap(await browserApi.POST("/workspaces/", { body }));
}

export async function completeOnboarding(ws: string): Promise<WorkspaceRead> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/onboarding/complete", {
      params: { path: { workspace_id: ws } },
    }),
  );
}

export async function updateWorkspace(ws: string, body: WorkspaceUpdate): Promise<WorkspaceRead> {
  return unwrap(
    await browserApi.PATCH("/workspaces/{workspace_id}", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

/** Everything in it goes too: members, invitations, records, files. */
export async function deleteWorkspace(ws: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}", {
      params: { path: { workspace_id: ws } },
    }),
  );
}

export async function leaveWorkspace(ws: string): Promise<void> {
  unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/leave", {
      params: { path: { workspace_id: ws } },
    }),
  );
}

export async function changeMemberRole(
  ws: string,
  memberId: string,
  role: WorkspaceRole,
): Promise<MemberRead> {
  return unwrap(
    await browserApi.PATCH("/workspaces/{workspace_id}/members/{member_id}", {
      params: { path: { workspace_id: ws, member_id: memberId } },
      body: { role },
    }),
  );
}

export async function removeMember(ws: string, memberId: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/members/{member_id}", {
      params: { path: { workspace_id: ws, member_id: memberId } },
    }),
  );
}

export async function createInvite(ws: string, body: InviteCreate): Promise<InviteRead> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/invites", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

/** A fresh link; the previous one stops working. */
export async function resendInvite(ws: string, inviteId: string): Promise<InviteRead> {
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
export async function acceptInvite(token: string): Promise<WorkspaceRead> {
  return unwrap(await browserApi.POST("/invites/{token}/accept", { params: { path: { token } } }));
}

/** Without the link: one of the caller's own. */
export async function acceptPendingInvite(inviteId: string): Promise<WorkspaceRead> {
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
