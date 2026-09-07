import type { ContactStatus, TaskStatus } from "@alloy/api-client";

import { Badge } from "@/components/ui/badge";
import { contactStatusLabels, taskStatusLabels } from "@/lib/labels";

const contactVariants = {
  lead: "secondary",
  active: "default",
  inactive: "outline",
} as const;

export function ContactStatusBadge({ status }: { status: ContactStatus }) {
  return <Badge variant={contactVariants[status]}>{contactStatusLabels[status]}</Badge>;
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge variant={status === "done" ? "outline" : "secondary"}>{taskStatusLabels[status]}</Badge>
  );
}
