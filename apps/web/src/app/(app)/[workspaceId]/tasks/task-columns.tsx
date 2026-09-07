"use client";

import type { TaskRead } from "@alloy/api-client";
import { MoreHorizontalIcon, PencilIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";

import { createDataTableColumnHelper, SortableHeader } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime, formatRelativeDays, isBeforeToday } from "@/lib/dates";
import type { WorkspacePaths } from "@/lib/routes";
import { cn } from "@/lib/utils";

import type { useTaskMutations } from "./use-task-mutations";

const column = createDataTableColumnHelper<TaskRead>();

export function taskColumns({
  timeZone,
  paths,
  actions,
}: {
  timeZone: string;
  paths: WorkspacePaths;
  /** Null makes the table read-only: no checkbox, no edit, no row menu. */
  actions: ReturnType<typeof useTaskMutations> | null;
}) {
  const statusColumn = column.accessor("status", {
    header: "",
    cell: ({ row }) => (
      <Checkbox
        checked={row.original.status === "done"}
        disabled={actions?.pendingStatusId === row.original.id}
        onCheckedChange={(checked) => actions?.setStatus(row.original, checked ? "done" : "open")}
        aria-label={`Mark "${row.original.title}" ${row.original.status === "done" ? "open" : "done"}`}
      />
    ),
    enableSorting: false,
  });

  const actionsColumn = column.display({
    id: "actions",
    cell: ({ row }) => (
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Actions for "${row.original.title}"`}
              />
            }
          >
            <MoreHorizontalIcon />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions?.openEdit(row.original)}>
              <PencilIcon /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onClick={() => actions?.confirmDelete(row.original)}
            >
              <Trash2Icon /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    ),
  });

  return column.columns([
    ...(actions ? [statusColumn] : []),
    column.accessor("title", {
      header: ({ column }) => <SortableHeader column={column}>Task</SortableHeader>,
      cell: ({ row }) => (
        <div className="flex flex-col">
          {actions ? (
            <button
              type="button"
              className={cn(
                "text-left font-medium hover:underline",
                row.original.status === "done" && "text-muted-foreground line-through",
              )}
              onClick={() => actions.openEdit(row.original)}
            >
              {row.original.title}
            </button>
          ) : (
            <span
              className={cn(
                "font-medium",
                row.original.status === "done" && "text-muted-foreground line-through",
              )}
            >
              {row.original.title}
            </span>
          )}
          {row.original.notes && (
            <span className="line-clamp-1 text-xs text-muted-foreground">{row.original.notes}</span>
          )}
        </div>
      ),
    }),
    column.accessor((row) => row.due_at ?? undefined, {
      id: "due_at",
      header: ({ column }) => <SortableHeader column={column}>Due</SortableHeader>,
      cell: ({ row }) => {
        const { due_at, status } = row.original;
        if (!due_at) return <span className="text-muted-foreground">–</span>;
        const overdue = status === "open" && isBeforeToday(due_at, timeZone);
        return (
          <span
            title={formatDateTime(due_at, timeZone)}
            className={cn(overdue && "font-medium text-destructive")}
          >
            {formatRelativeDays(due_at, timeZone)}
          </span>
        );
      },
      sortFn: "basic",
      sortUndefined: "last",
    }),
    column.accessor((row) => row.contact?.name ?? "", {
      id: "contact",
      header: ({ column }) => <SortableHeader column={column}>Contact</SortableHeader>,
      cell: ({ row }) =>
        row.original.contact ? (
          <Link href={paths.contact(row.original.contact.id)} className="hover:underline">
            {row.original.contact.name}
          </Link>
        ) : (
          <span className="text-muted-foreground">–</span>
        ),
    }),
    column.accessor((row) => row.company?.name ?? "", {
      id: "company",
      header: ({ column }) => <SortableHeader column={column}>Company</SortableHeader>,
      cell: ({ row }) =>
        row.original.company ? (
          <Link href={paths.company(row.original.company.id)} className="hover:underline">
            {row.original.company.name}
          </Link>
        ) : (
          <span className="text-muted-foreground">–</span>
        ),
    }),
    ...(actions ? [actionsColumn] : []),
  ]);
}
