import { z } from "zod";

import { workspaceRoles } from "@/features/workspaces/roles";

export const inviteSchema = z.object({
  email: z.email("Enter a valid email address"),
  role: z.enum(workspaceRoles),
});

export type InviteInput = z.input<typeof inviteSchema>;
