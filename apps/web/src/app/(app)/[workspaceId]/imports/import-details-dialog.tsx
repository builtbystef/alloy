"use client";

import type { ImportRead } from "@alloy/api-client";

import { ImportStatusBadge } from "@/components/status-badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDateTime } from "@/lib/dates";
import { importKindLabels } from "@/lib/labels";

/** The API keeps this many row errors; past it, the count is all there is. */
const MAX_ROW_ERRORS = 100;

/** Counts and the rejected rows of a finished import, with the file's line numbers. */
export function ImportDetailsDialog({
  record,
  timeZone,
  onOpenChange,
}: {
  record: ImportRead | null;
  timeZone: string;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={record !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {record && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {record.filename} <ImportStatusBadge status={record.status} />
              </DialogTitle>
              <DialogDescription>
                {importKindLabels[record.kind]}
                {record.requested_by && ` · by ${record.requested_by.email}`}
                {record.finished_at &&
                  ` · finished ${formatDateTime(record.finished_at, timeZone)}`}
              </DialogDescription>
            </DialogHeader>
            {record.status === "failed" ? (
              <p className="text-destructive">{record.error}</p>
            ) : (
              <dl className="grid grid-cols-4 gap-2 rounded-lg border bg-muted/30 p-3 text-center">
                <Stat label="Rows" value={record.total_rows} />
                <Stat label="Created" value={record.created_count} />
                <Stat label="Skipped" value={record.skipped_count} />
                <Stat label="Rejected" value={record.failed_count} />
              </dl>
            )}
            {record.errors.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="font-medium">
                  Rejected rows
                  {record.failed_count > MAX_ROW_ERRORS && (
                    <span className="font-normal text-muted-foreground">
                      {" "}
                      (first {MAX_ROW_ERRORS} of {record.failed_count})
                    </span>
                  )}
                </p>
                <ul className="max-h-72 divide-y overflow-y-auto rounded-lg border">
                  {record.errors.map((error) => (
                    <li key={error.row} className="flex gap-3 px-3 py-1.5">
                      <span className="w-14 shrink-0 text-muted-foreground tabular-nums">
                        Line {error.row}
                      </span>
                      <span className="min-w-0 break-words">{error.message}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <DialogFooter showCloseButton />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
