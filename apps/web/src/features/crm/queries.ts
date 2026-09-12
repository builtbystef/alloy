import type { QueryClient } from "@tanstack/react-query";

import { attachmentKeys } from "@/features/crm/attachments/queries";
import { companyKeys } from "@/features/crm/companies/queries";
import { contactKeys } from "@/features/crm/contacts/queries";
import { taskKeys } from "@/features/crm/tasks/queries";

/**
 * Drop every CRM query after a write. The entities reference each other
 * (a task embeds its contact, a completed task logs an activity, deleting a
 * company clears links, an import creates both), so anything narrower would
 * have to know those rules.
 */
export async function invalidateCrm(queryClient: QueryClient): Promise<void> {
  await Promise.all(
    [contactKeys.all, companyKeys.all, taskKeys.all, attachmentKeys.all].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}
