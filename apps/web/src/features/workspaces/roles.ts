import type { WorkspaceRole } from "@alloy/api-client";

/** Highest first; the order is what `canManageRole` compares. */
export const workspaceRoles = [
  "owner",
  "admin",
  "member",
  "viewer",
] as const satisfies readonly WorkspaceRole[];

export const roleLabels: Record<WorkspaceRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

export const roleDescriptions: Record<WorkspaceRole, string> = {
  owner: "Everything, including deleting the workspace.",
  admin: "Edits records, manages members and settings.",
  member: "Edits contacts, companies, and tasks.",
  viewer: "Read-only.",
};

/**
 * Mirrors `can_manage_role` in the API, so the UI offers only what the request
 * would accept: owners manage everyone, others only roles below their own.
 */
export function canManageRole(actor: WorkspaceRole, target: WorkspaceRole): boolean {
  if (actor === "owner") return true;
  return workspaceRoles.indexOf(actor) < workspaceRoles.indexOf(target);
}

export function assignableRoles(actor: WorkspaceRole): WorkspaceRole[] {
  return workspaceRoles.filter((role) => canManageRole(actor, role));
}
