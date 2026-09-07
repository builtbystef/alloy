import type { WorkspaceRole } from "@alloy/api-client";

import { workspaceRoles } from "@/lib/schemas";

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
