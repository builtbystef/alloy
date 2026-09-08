"use client";

import type { ImportRead } from "@alloy/api-client";
import { Loader2Icon } from "lucide-react";

import { createDataTableColumnHelper } from "@/components/data-table";
import { ImportStatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/bytes";
import { formatDateTime, formatRelativeDays } from "@/lib/dates";
import { importKindLabels } from "@/lib/labels";
import { isImportActive } from "@/lib/queries";

const column = createDataTableColumnHelper<ImportRead>();

/** Sorting is off: the API already orders newest first, and the list is short. */
export function importColumns({
  timeZone,
  onSelect,
}: {
  timeZone: string;
  onSelect: (record: ImportRead) => void;
}) {
  return column.columns([
    column.accessor("filename", {
      header: "File",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-medium">{row.original.filename}</span>
          <span className="text-xs text-muted-foreground">{formatBytes(row.original.size)}</span>
        </div>
      ),
      enableSorting: false,
    }),
    column.accessor("kind", {
      header: "Kind",
      cell: ({ getValue }) => importKindLabels[getValue()],
      enableSorting: false,
    }),
    column.accessor("status", {
      header: "Status",
      cell: ({ row }) => (
        <span className="inline-flex items-center gap-2">
          <ImportStatusBadge status={row.original.status} />
          {isImportActive(row.original) && (
            <Loader2Icon className="size-3.5 animate-spin text-muted-foreground" />
          )}
        </span>
      ),
      enableSorting: false,
    }),
    column.display({
      id: "result",
      header: "Result",
      cell: ({ row }) => <Result record={row.original} />,
    }),
    column.accessor("created_at", {
      header: "Requested",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span title={formatDateTime(row.original.created_at, timeZone)}>
            {formatRelativeDays(row.original.created_at, timeZone)}
          </span>
          {row.original.requested_by && (
            <span className="truncate text-xs text-muted-foreground">
              {row.original.requested_by.email}
            </span>
          )}
        </div>
      ),
      enableSorting: false,
    }),
    column.display({
      id: "actions",
      cell: ({ row }) =>
        row.original.finished_at ? (
          <div className="flex justify-end">
            <Button variant="ghost" size="sm" onClick={() => onSelect(row.original)}>
              Details
            </Button>
          </div>
        ) : null,
    }),
  ]);
}

function Result({ record }: { record: ImportRead }) {
  if (record.status === "failed") {
    return <span className="text-destructive">{record.error}</span>;
  }
  if (record.status !== "done") {
    return <span className="text-muted-foreground">–</span>;
  }
  return (
    <span className="tabular-nums">
      {record.created_count} created
      {record.skipped_count > 0 && (
        <span className="text-muted-foreground">, {record.skipped_count} skipped</span>
      )}
      {record.failed_count > 0 && (
        <span className="text-destructive">, {record.failed_count} rejected</span>
      )}
    </span>
  );
}
