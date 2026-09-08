"use client";

import type { ImportRead } from "@alloy/api-client";
import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { DataTable } from "@/components/data-table";
import { browserApi } from "@/lib/api-browser";
import { importKindLabels } from "@/lib/labels";
import { importListQuery, invalidateCrm, isImportActive } from "@/lib/queries";
import { useWorkspace } from "@/lib/workspace";

import { importColumns } from "./import-columns";
import { ImportDetailsDialog } from "./import-details-dialog";

function outcome(record: ImportRead): string {
  const what = importKindLabels[record.kind].toLowerCase();
  if (record.status === "failed") return `${record.filename} failed: ${record.error}`;
  const parts = [`${record.created_count} ${what} created`];
  if (record.skipped_count) parts.push(`${record.skipped_count} skipped`);
  if (record.failed_count) parts.push(`${record.failed_count} rows rejected`);
  return `${record.filename}: ${parts.join(", ")}.`;
}

/**
 * The history, newest first. The query polls while an import is running;
 * when one this page watched finishes, the outcome is announced and the
 * contact and company lists are dropped, since the worker just changed them.
 */
export function ImportsTable({ timeZone }: { timeZone: string }) {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const { data: imports } = useSuspenseQuery(importListQuery(browserApi, workspaceId));
  const [selected, setSelected] = useState<ImportRead | null>(null);
  const watched = useRef(new Set<string>());

  useEffect(() => {
    const finished: ImportRead[] = [];
    for (const record of imports) {
      if (isImportActive(record)) watched.current.add(record.id);
      else if (watched.current.delete(record.id)) finished.push(record);
    }
    for (const record of finished) {
      if (record.status === "failed") toast.error(outcome(record));
      else toast.success(outcome(record));
    }
    if (finished.length > 0) void invalidateCrm(queryClient);
  }, [imports, queryClient]);

  return (
    <div className="flex flex-col gap-4">
      <DataTable<ImportRead>
        columns={importColumns({ timeZone, onSelect: setSelected })}
        data={imports}
        emptyMessage="No imports yet."
      />
      <ImportDetailsDialog
        record={selected}
        timeZone={timeZone}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      />
    </div>
  );
}
