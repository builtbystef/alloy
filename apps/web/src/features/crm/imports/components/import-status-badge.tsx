import type { ImportStatus } from "@alloy/api-client";

import { Badge } from "@/components/ui/badge";
import { importStatusLabels } from "@/features/crm/imports/labels";

const variants = {
  pending: "outline",
  queued: "secondary",
  running: "secondary",
  done: "default",
  failed: "destructive",
} as const;

export function ImportStatusBadge({ status }: { status: ImportStatus }) {
  return <Badge variant={variants[status]}>{importStatusLabels[status]}</Badge>;
}
