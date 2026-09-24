import { z } from "zod";

import { requiredText } from "@/lib/validation";

export const workspaceSchema = z.object({
  name: requiredText("Name", 100),
});

export type WorkspaceInput = z.input<typeof workspaceSchema>;
