import type { TaskStatus } from "@alloy/api-client";

import { Badge } from "@/components/ui/badge";
import { taskStatusLabels } from "@/features/crm/tasks/labels";

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge variant={status === "done" ? "outline" : "secondary"}>{taskStatusLabels[status]}</Badge>
  );
}
