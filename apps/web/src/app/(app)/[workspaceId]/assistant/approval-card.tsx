"use client";

import { getToolName } from "ai";

import {
  Confirmation,
  ConfirmationAccepted,
  ConfirmationAction,
  ConfirmationActions,
  ConfirmationRejected,
  ConfirmationRequest,
  ConfirmationTitle,
} from "@/components/chat/confirmation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import type { ApprovalPreview, ChatToolPart } from "./chat-types";
import { toolLabel } from "./tools";

/** How many rows of the preview are shown; the title says how many there are. */
const MAX_ROWS = 25;

/**
 * The approve / deny card for a paused tool call. Shows the API's preview (a
 * title and a small table of what is about to happen) when it has one, and
 * falls back to the tool's name and item count when it does not.
 */
export function ApprovalCard({
  part,
  preview,
  onRespond,
}: {
  part: ChatToolPart;
  preview: ApprovalPreview | undefined;
  onRespond: (approved: boolean) => void;
}) {
  const approval = "approval" in part ? part.approval : undefined;
  const title = preview?.title ?? fallbackTitle(part);
  const hidden = preview ? preview.total - Math.min(preview.rows.length, MAX_ROWS) : 0;

  return (
    <Confirmation approval={approval} state={part.state} data-testid="approval-card">
      <ConfirmationTitle className="flex flex-col gap-2">
        <span className="font-medium text-foreground">{title}</span>
        {preview && preview.rows.length > 0 && (
          <div className="overflow-x-auto rounded-md border bg-background">
            <Table>
              <TableHeader>
                <TableRow>
                  {preview.columns.map((column) => (
                    <TableHead key={column}>{column}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.rows.slice(0, MAX_ROWS).map((row, index) => (
                  <TableRow key={index}>
                    {row.map((cell, column) => (
                      <TableCell key={column} className="max-w-64 truncate">
                        {cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {hidden > 0 && <span className="text-xs">…and {hidden} more.</span>}
        <ConfirmationRequest>
          <span>The assistant is waiting for your decision.</span>
        </ConfirmationRequest>
        <ConfirmationAccepted>
          <span>Approved.</span>
        </ConfirmationAccepted>
        <ConfirmationRejected>
          <span>Denied{approval?.reason ? `: ${approval.reason}` : "."}</span>
        </ConfirmationRejected>
      </ConfirmationTitle>
      <ConfirmationActions>
        <ConfirmationAction variant="outline" onClick={() => onRespond(false)}>
          Deny
        </ConfirmationAction>
        <ConfirmationAction onClick={() => onRespond(true)}>Approve</ConfirmationAction>
      </ConfirmationActions>
    </Confirmation>
  );
}

function fallbackTitle(part: ChatToolPart): string {
  const name = getToolName(part);
  const input = part.input;
  let count: number | null = null;
  if (input && typeof input === "object") {
    const list = Object.values(input as Record<string, unknown>).find(Array.isArray);
    if (list) count = list.length;
  }
  const label = toolLabel(name)
    .replace(/ing\b/, "e")
    .replace(/^Deletee/, "Delete");
  return count === null ? label : `${label} (${count} ${count === 1 ? "item" : "items"})`;
}
