import type { ContactStatus } from "@alloy/api-client";

import { Badge } from "@/components/ui/badge";
import { contactStatusLabels } from "@/features/crm/contacts/labels";

const variants = {
  lead: "secondary",
  active: "default",
  inactive: "outline",
} as const;

export function ContactStatusBadge({ status }: { status: ContactStatus }) {
  return <Badge variant={variants[status]}>{contactStatusLabels[status]}</Badge>;
}
