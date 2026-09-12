import { z } from "zod";

import { workspaceRoles } from "@/features/workspaces/roles";
import { requiredText } from "@/lib/validation";

export const workspaceSchema = z.object({
  name: requiredText("Name", 100),
});

export const inviteSchema = z.object({
  email: z.email("Enter a valid email address"),
  role: z.enum(workspaceRoles),
});

export type WorkspaceInput = z.input<typeof workspaceSchema>;
export type InviteInput = z.input<typeof inviteSchema>;
